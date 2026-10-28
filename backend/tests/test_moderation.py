"""Test suite for R4.2 Admin Report Moderation, Audit and Concurrency Guard."""

from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import reset_rate_limits
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.reports import ModerationAction, Report, ReportEvidence
from app.models.users import Role, User


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    user_role = Role(id=uuid.uuid4(), name="user", description="Người dùng chuẩn")
    admin_role = Role(id=uuid.uuid4(), name="admin", description="Quản trị viên")
    session.add_all([user_role, admin_role])
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    reset_rate_limits()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user_and_token(client: TestClient, email: str, role_name: str = "user") -> str:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure_password_15_chars",
            "full_name": "Test User",
        },
    )
    assert res.status_code == 201
    token = res.json()["access_token"]

    if role_name == "admin":
        # Cập nhật quyền admin trong DB
        db = next(app.dependency_overrides[get_db]())
        user = db.query(User).filter_by(email=email).first()
        admin_role = db.query(Role).filter_by(name="admin").first()
        user.role_id = admin_role.id
        db.commit()

    return token


def test_admin_route_requires_admin_role(client: TestClient):
    """Người dùng thông thường bị chặn 403 Forbidden khi cố truy cập route admin."""
    user_token = create_user_and_token(client, "normal_user@example.com", "user")
    headers = {"Authorization": f"Bearer {user_token}"}

    res = client.get("/api/v1/admin/reports", headers=headers)
    assert res.status_code == 403
    assert res.json()["detail"] == "Yêu cầu quyền quản trị viên"


def test_admin_route_requires_auth(client: TestClient):
    """Không có token bị từ chối 401 Unauthorized."""
    res = client.get("/api/v1/admin/reports")
    assert res.status_code == 401


def test_admin_list_and_filter_reports(client: TestClient, db_session):
    """Admin xem danh sách hàng đợi báo cáo và lọc theo trạng thái."""
    admin_token = create_user_and_token(client, "admin1@example.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token = create_user_and_token(client, "user_rep@example.com", "user")
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Gửi 2 báo cáo
    client.post(
        "/api/v1/reports",
        json={"reason": "Lừa đảo 1", "description": "Mô tả báo cáo số 1"},
        headers=user_headers,
    )
    client.post(
        "/api/v1/reports",
        json={"reason": "Lừa đảo 2", "description": "Mô tả báo cáo số 2"},
        headers=user_headers,
    )

    # Admin xem danh sách
    res = client.get("/api/v1/admin/reports", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["reporter_email"] == "user_rep@example.com"

    # Lọc theo status pending
    res_pending = client.get("/api/v1/admin/reports?status=pending", headers=admin_headers)
    assert res_pending.status_code == 200
    assert res_pending.json()["total"] == 2

    # Lọc theo status verified (chưa có)
    res_verified = client.get("/api/v1/admin/reports?status=verified", headers=admin_headers)
    assert res_verified.status_code == 200
    assert res_verified.json()["total"] == 0


def test_admin_moderation_success(client: TestClient):
    """Admin kiểm duyệt báo cáo, cập nhật trạng thái và ghi nhận lịch sử."""
    admin_token = create_user_and_token(client, "admin_mod@example.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token = create_user_and_token(client, "user_mod@example.com", "user")
    user_headers = {"Authorization": f"Bearer {user_token}"}

    rep_res = client.post(
        "/api/v1/reports",
        json={
            "reason": "Thu phí trước",
            "description": "Bắt chuyển 500k tiền giữ chỗ làm việc",
            "evidences": [{"evidence_type": "text", "content": "Tin nhắn chuyển khoản"}],
        },
        headers=user_headers,
    )
    report_id = rep_res.json()["id"]

    # Admin thực hiện kiểm duyệt
    mod_res = client.post(
        f"/api/v1/admin/reports/{report_id}/moderation",
        json={
            "action_type": "verify",
            "to_status": "verified",
            "decision_summary": "Đã xác nhận dấu hiệu thu phí bất hợp pháp qua đối chiếu bằng chứng.",
            "private_note": "Tài khoản ngân hàng trùng danh sách đen.",
            "expected_version": 1,
        },
        headers=admin_headers,
    )
    assert mod_res.status_code == 200
    data = mod_res.json()
    assert data["status"] == "verified"
    assert data["version"] == 2
    assert len(data["moderation_actions"]) == 1
    action = data["moderation_actions"][0]
    assert action["action_type"] == "verify"
    assert action["from_status"] == "pending"
    assert action["to_status"] == "verified"
    assert action["private_note"] == "Tài khoản ngân hàng trùng danh sách đen."
    assert action["moderator_name"] == "Test User"


def test_optimistic_concurrency_guard_prevents_overwrite(client: TestClient):
    """Chống hai admin ghi đè quyết định của nhau: admin 2 bị chặn 409 Conflict khi gửi version cũ."""
    admin1_token = create_user_and_token(client, "admin_race1@example.com", "admin")
    admin2_token = create_user_and_token(client, "admin_race2@example.com", "admin")

    user_token = create_user_and_token(client, "user_race@example.com", "user")
    rep_res = client.post(
        "/api/v1/reports",
        json={"reason": "Nhiệm vụ nạp tiền", "description": "Lừa đảo giật đơn nạp tiền"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    report_id = rep_res.json()["id"]

    # Cả hai admin đều đọc báo cáo ở version 1
    # Admin 1 thực hiện duyệt trước với expected_version = 1
    res1 = client.post(
        f"/api/v1/admin/reports/{report_id}/moderation",
        json={
            "action_type": "review",
            "to_status": "under_review",
            "decision_summary": "Đang tiến hành xác minh bằng chứng.",
            "expected_version": 1,
        },
        headers={"Authorization": f"Bearer {admin1_token}"},
    )
    assert res1.status_code == 200
    assert res1.json()["version"] == 2
    assert res1.json()["status"] == "under_review"

    # Admin 2 vẫn gửi quyết định dựa trên version 1 cũ -> Bị từ chối 409 Conflict
    res2 = client.post(
        f"/api/v1/admin/reports/{report_id}/moderation",
        json={
            "action_type": "reject",
            "to_status": "rejected",
            "decision_summary": "Không đủ bằng chứng xác thực.",
            "expected_version": 1,  # Đã cũ, hiện tại là 2!
        },
        headers={"Authorization": f"Bearer {admin2_token}"},
    )
    assert res2.status_code == 409
    assert "REPORT_VERSION_CONFLICT" in res2.json()["detail"]

    # Sau khi tải lại dữ liệu mới (version 2), Admin 2 có thể gửi lại với expected_version = 2
    res2_retry = client.post(
        f"/api/v1/admin/reports/{report_id}/moderation",
        json={
            "action_type": "reject",
            "to_status": "rejected",
            "decision_summary": "Không đủ bằng chứng xác thực sau khi xem xét lại.",
            "expected_version": 2,
        },
        headers={"Authorization": f"Bearer {admin2_token}"},
    )
    assert res2_retry.status_code == 200
    assert res2_retry.json()["version"] == 3
    assert res2_retry.json()["status"] == "rejected"
    assert len(res2_retry.json()["moderation_actions"]) == 2
