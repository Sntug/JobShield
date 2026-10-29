"""Test suite for R4.4 Public Warnings, Superseding, and Withdrawal."""

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
from app.models.reports import PublicWarning
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


def create_admin_token(client: TestClient, email: str = "admin_warn@example.com") -> str:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure_password_15_chars",
            "full_name": "Admin Warnings",
        },
    )
    assert res.status_code == 201
    token = res.json()["access_token"]

    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter_by(email=email).first()
    admin_role = db.query(Role).filter_by(name="admin").first()
    user.role_id = admin_role.id
    db.commit()

    return token


def test_public_warnings_full_lifecycle(client: TestClient):
    """Vòng đời hoàn chỉnh của bản cảnh báo: Xuất bản -> Đọc công khai -> Đính chính -> Thu hồi."""
    admin_token = create_admin_token(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin xuất bản cảnh báo mới
    create_payload = {
        "title_vi": "Cảnh báo thủ đoạn mạo danh Tập đoàn X tuyển dụng cộng tác viên",
        "public_summary_vi": "Các đối tượng sử dụng fanpage giả mạo mang tên Tập đoàn X để tuyển CTV làm nhiệm vụ nạp tiền và chiếm đoạt tài sản.",
        "public_sources_snapshot": [
            {"label_vi": "Thông báo chính thức từ Tập đoàn X", "url": "https://tapdoanx.example/canh-bao"}
        ],
    }
    pub_res = client.post("/api/v1/admin/warnings", json=create_payload, headers=admin_headers)
    assert pub_res.status_code == 201
    warning_v1 = pub_res.json()
    assert warning_v1["status"] == "published"
    assert warning_v1["revision"] == 1
    assert warning_v1["previous_warning_id"] is None
    warning_v1_id = warning_v1["id"]

    # 2. Khách vãng lai (không token) đọc danh sách và chi tiết cảnh báo
    list_res = client.get("/api/v1/warnings")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["items"][0]["id"] == warning_v1_id

    detail_res = client.get(f"/api/v1/warnings/{warning_v1_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["title_vi"] == create_payload["title_vi"]

    # 3. Admin đính chính / thay thế cảnh báo (supersede) với revision mới
    supersede_payload = {
        "title_vi": "Cảnh báo bổ sung: Thủ đoạn mạo danh Tập đoàn X trên Telegram",
        "public_summary_vi": "Cập nhật danh sách các nhóm Telegram giả mạo yêu cầu chuyển tiền cọc làm nhiệm vụ.",
        "public_sources_snapshot": [
            {"label_vi": "Thông báo số 2 từ Tập đoàn X", "url": "https://tapdoanx.example/canh-bao-2"}
        ],
    }
    sup_res = client.post(
        f"/api/v1/admin/warnings/{warning_v1_id}/supersede",
        json=supersede_payload,
        headers=admin_headers,
    )
    assert sup_res.status_code == 200
    warning_v2 = sup_res.json()
    assert warning_v2["status"] == "published"
    assert warning_v2["revision"] == 2
    assert warning_v2["previous_warning_id"] == warning_v1_id
    warning_v2_id = warning_v2["id"]

    # Bản cũ v1 đã chuyển sang trạng thái superseded, không còn xuất hiện trong danh sách active public
    list_after_sup = client.get("/api/v1/warnings")
    assert list_after_sup.status_code == 200
    assert list_after_sup.json()["total"] == 1
    assert list_after_sup.json()["items"][0]["id"] == warning_v2_id

    # 4. Admin thu hồi (withdraw) cảnh báo v2 kèm lý do
    withdraw_payload = {
        "withdrawal_reason_vi": "Đối tượng giả mạo đã bị cơ quan chức năng triệt phá và kênh lừa đảo đã bị gỡ bỏ."
    }
    with_res = client.post(
        f"/api/v1/admin/warnings/{warning_v2_id}/withdraw",
        json=withdraw_payload,
        headers=admin_headers,
    )
    assert with_res.status_code == 200
    warning_withdrawn = with_res.json()
    assert warning_withdrawn["status"] == "withdrawn"
    assert warning_withdrawn["withdrawal_reason_vi"] == withdraw_payload["withdrawal_reason_vi"]
    assert warning_withdrawn["withdrawn_at"] is not None

    # Sau khi thu hồi, danh sách public rỗng
    list_after_with = client.get("/api/v1/warnings")
    assert list_after_with.status_code == 200
    assert list_after_with.json()["total"] == 0

    # Khách truy cập trực tiếp ID đã thu hồi -> 404
    detail_with_res = client.get(f"/api/v1/warnings/{warning_v2_id}")
    assert detail_with_res.status_code == 200
    assert detail_with_res.json()["status"] == "withdrawn"
    assert detail_with_res.json()["public_summary_vi"] == ""


def test_withdrawn_warning_keeps_public_tombstone(client):
    headers = {"Authorization": f"Bearer {create_admin_token(client)}"}
    payload = {"title_vi": "Warning to withdraw", "public_summary_vi": "Content that must disappear after withdrawal.", "public_sources_snapshot": [{"label_vi": "Evidence", "url": "https://example.com/evidence"}]}
    warning = client.post("/api/v1/admin/warnings", headers=headers, json=payload).json()
    wid = warning["id"]
    assert client.post(f"/api/v1/admin/warnings/{wid}/withdraw", headers=headers, json={"withdrawal_reason_vi": "Incorrect evidence; withdrawn."}).status_code == 200
    response = client.get(f"/api/v1/warnings/{wid}")
    assert response.status_code == 200
    tombstone = response.json()
    assert tombstone["status"] == "withdrawn"
    assert tombstone["withdrawal_reason_vi"] == "Incorrect evidence; withdrawn."
    assert tombstone["public_summary_vi"] == ""
    assert tombstone["public_sources_snapshot"] == []
    assert client.post(f"/api/v1/admin/warnings/{wid}/supersede", headers=headers, json=payload).status_code == 409
