"""Test suite for R4.1 User Community Reporting."""

from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import reset_rate_limits
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analyses import Analysis
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


def register_user(client: TestClient, email: str, name: str = "Test User") -> str:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure_password_15_chars",
            "full_name": name,
        },
    )
    assert res.status_code == 201
    return res.json()["access_token"]


def test_submit_report_unauthenticated_fails(client: TestClient):
    """Yêu cầu gửi báo cáo khi chưa đăng nhập bị từ chối 401."""
    res = client.post(
        "/api/v1/reports",
        json={
            "reason": "Lừa đảo nạp tiền",
            "description": "Yêu cầu nạp 500k làm nhiệm vụ rồi khóa liên lạc",
        },
    )
    assert res.status_code == 401


def test_submit_report_validation_errors(client: TestClient):
    """Kiểm tra validation: thiếu lý do, mô tả quá ngắn hoặc URL bằng chứng sai."""
    token = register_user(client, "user_val@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Thiếu reason
    res = client.post(
        "/api/v1/reports",
        json={"reason": "   ", "description": "Mô tả hợp lệ cho báo cáo"},
        headers=headers,
    )
    assert res.status_code == 422

    # Mô tả quá ngắn (< 5 ký tự)
    res = client.post(
        "/api/v1/reports",
        json={"reason": "Lý do", "description": "Ngắn"},
        headers=headers,
    )
    assert res.status_code == 422

    # URL bằng chứng không hợp lệ
    res = client.post(
        "/api/v1/reports",
        json={
            "reason": "Lừa đảo",
            "description": "Mô tả chi tiết hợp lệ",
            "evidences": [{"evidence_type": "url", "source_url": "ftp://invalid-url"}],
        },
        headers=headers,
    )
    assert res.status_code == 422


def test_submit_report_success(client: TestClient):
    """Gửi báo cáo thành công với đầy đủ thông tin và bằng chứng."""
    token = register_user(client, "reporter1@example.com", "Người báo cáo 1")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "reason": "Thu phí tuyển dụng trước",
        "description": "Bắt đóng 300.000 VNĐ tiền đồng phục và tiền hồ sơ trước khi phỏng vấn",
        "evidences": [
            {
                "evidence_type": "text",
                "content": "Đoạn chat: Em chuyển 300k vào số tài khoản 123456 để giữ chỗ nhé",
            },
            {
                "evidence_type": "url",
                "source_url": "https://example.com/fake-job-post",
            },
        ],
    }

    res = client.post("/api/v1/reports", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending"
    assert data["version"] == 1
    assert data["reason"] == payload["reason"]
    assert len(data["evidences"]) == 2
    assert data["evidences"][0]["evidence_type"] == "text"
    assert data["evidences"][1]["evidence_type"] == "url"


def test_user_reports_isolation(client: TestClient):
    """Hai người dùng khác nhau không xem được báo cáo của nhau."""
    token_a = register_user(client, "user_a@example.com", "User A")
    token_b = register_user(client, "user_b@example.com", "User B")

    # User A gửi báo cáo
    res_a = client.post(
        "/api/v1/reports",
        json={"reason": "Báo cáo A", "description": "Nội dung báo cáo của User A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 201
    report_a_id = res_a.json()["id"]

    # User B gửi báo cáo
    res_b = client.post(
        "/api/v1/reports",
        json={"reason": "Báo cáo B", "description": "Nội dung báo cáo của User B"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 201

    # User A xem danh sách báo cáo của mình: chỉ thấy 1 cái
    list_a = client.get("/api/v1/reports", headers={"Authorization": f"Bearer {token_a}"})
    assert list_a.status_code == 200
    assert list_a.json()["total"] == 1
    assert list_a.json()["items"][0]["id"] == report_a_id

    # User B cố tình truy cập trực tiếp ID của User A -> 404 Not Found
    res_b_view_a = client.get(
        f"/api/v1/reports/{report_a_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_view_a.status_code == 404


def test_user_cannot_see_private_moderator_note(client: TestClient, db_session):
    """Người dùng không thấy ghi chú nội bộ (private_note) của ban quản trị khi đọc kết quả."""
    token = register_user(client, "reporter_privacy@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/reports",
        json={"reason": "Mạo danh công ty", "description": "Dùng tên công ty lớn lừa đảo"},
        headers=headers,
    )
    report_id = res.json()["id"]

    # Giả lập admin ghi nhận kiểm duyệt có private_note
    admin_user = User(
        id=uuid.uuid4(),
        role_id=db_session.query(Role).filter_by(name="admin").first().id,
        email="admin_internal@example.com",
        password_hash="dummy",
        full_name="Admin Internal",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(admin_user)
    db_session.commit()

    action = ModerationAction(
        report_id=uuid.UUID(report_id),
        moderator_id=admin_user.id,
        action_type="verify",
        from_status="pending",
        to_status="verified",
        report_version_after=2,
        decision_summary="Xác nhận dấu hiệu mạo danh dựa trên đối chiếu tên miền.",
        private_note="BÍ MẬT QUẢN TRỊ: IP người gửi trùng với nghi vấn trước đó.",
    )
    report_obj = db_session.query(Report).filter_by(id=uuid.UUID(report_id)).first()
    report_obj.status = "verified"
    report_obj.version = 2
    db_session.add(action)
    db_session.commit()

    # Người dùng đọc lại báo cáo của mình
    detail_res = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["status"] == "verified"
    assert len(data["moderation_actions"]) == 1
    action_data = data["moderation_actions"][0]
    assert action_data["decision_summary"] == "Xác nhận dấu hiệu mạo danh dựa trên đối chiếu tên miền."
    # Chắc chắn không có trường private_note trong response gửi người dùng
    assert "private_note" not in action_data


def test_report_rejects_another_users_analysis(client):
    owner = register_user(client, "analysis_owner@example.com")
    other = register_user(client, "other_reporter@example.com")
    analysis = client.post("/api/v1/analyses", json={"text": "Đóng phí hồ sơ trước khi nhận việc."}, headers={"Authorization": f"Bearer {owner}"}).json()
    response = client.post("/api/v1/reports", json={"reason": "Phí trước", "description": "Báo cáo phân tích người khác", "analysis_id": analysis["id"]}, headers={"Authorization": f"Bearer {other}"})
    assert response.status_code == 404
