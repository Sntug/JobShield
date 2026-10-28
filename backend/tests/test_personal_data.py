"""Comprehensive test suite for R2.2 and R2.3: Personal Data, Guest Claims, History, Saved Analyses, and Profile."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cli.cleanup import purge_expired_sessions
from app.core.rate_limit import reset_rate_limits
from app.core.security import generate_guest_token, hash_guest_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analyses import Analysis
from app.models.guest_sessions import GuestSession
from app.models.saved_analyses import SavedAnalysis
from app.models.users import AccessSession, Role, User


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
    session.add(user_role)
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
    """Helper đăng ký người dùng và trả về access token."""
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


def test_authenticated_analysis_creation(client: TestClient, db_session):
    """Tạo phân tích khi đã đăng nhập: gán user_id, session_id=None, expires_at=None."""
    token = register_user(client, "user_create@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/analyses",
        headers=headers,
        json={"text": "Tuyển dụng nhân viên nhập liệu online lương 50 triệu/tháng không yêu cầu kinh nghiệm"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["guest_session_token"] is None
    assert data["expires_at"] is None
    analysis_id = uuid.UUID(data["id"])

    # Kiểm tra trực tiếp trong DB
    analysis = db_session.query(Analysis).filter_by(id=analysis_id).first()
    assert analysis is not None
    assert analysis.user_id is not None
    assert analysis.session_id is None
    assert analysis.expires_at is None


def test_cross_user_isolation(client: TestClient):
    """User A không thể đọc hoặc xóa phân tích của User B (trả về 404)."""
    token_a = register_user(client, "user_a@example.com")
    token_b = register_user(client, "user_b@example.com")

    # User A tạo phân tích
    res_a = client.post(
        "/api/v1/analyses",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"text": "Tuyển lập trình viên Python bảo mật cao lương thỏa thuận."},
    )
    analysis_id = res_a.json()["id"]

    # User B cố đọc phân tích của User A -> 404
    res_b_get = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_get.status_code == 404

    # Khách không token hoặc token khách khác cố đọc -> 404
    res_guest_get = client.get(f"/api/v1/analyses/{analysis_id}")
    assert res_guest_get.status_code == 404

    # User B cố xóa phân tích của User A -> 404
    res_b_del = client.delete(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_del.status_code == 404

    # User A đọc thành công: 200
    res_a_get = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_get.status_code == 200

    # User A xóa thành công: 200
    res_a_del = client.delete(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_del.status_code == 200

    # Sau khi xóa, đọc lại -> 404
    res_a_after = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_after.status_code == 404


def test_claim_guest_analyses_flow(client: TestClient, db_session):
    """Quy trình nhận quyền phiên khách: chuyển owner, xóa guest_session, không thể replay."""
    # 1. Khách tạo 2 phân tích
    res1 = client.post(
        "/api/v1/analyses",
        json={"text": "Tuyển dụng việc nhẹ lương cao nộp tiền cọc đồng phục 500k"},
    )
    guest_token = res1.json()["guest_session_token"]
    assert guest_token is not None
    id1 = uuid.UUID(res1.json()["id"])

    res2 = client.post(
        "/api/v1/analyses",
        headers={"X-Guest-Session-Token": guest_token},
        json={"text": "Tuyển dụng giao hàng shopee thu nhập 10tr không đặt cọc"},
    )
    id2 = uuid.UUID(res2.json()["id"])

    # 2. Người dùng đăng nhập nhận quyền
    user_token = register_user(client, "claimer@example.com")
    headers = {"Authorization": f"Bearer {user_token}"}

    claim_res = client.post(
        "/api/v1/auth/claim-guest",
        headers=headers,
        json={"guest_session_token": guest_token},
    )
    assert claim_res.status_code == 200
    claim_data = claim_res.json()
    assert claim_data["claimed_count"] == 2
    assert set(claim_data["claimed_ids"]) == {str(id1), str(id2)}

    # 3. Kiểm tra DB: analyses đã chuyển sang user_id, expires_at=None, session_id=None
    a1 = db_session.query(Analysis).filter_by(id=id1).first()
    a2 = db_session.query(Analysis).filter_by(id=id2).first()
    assert a1.user_id is not None
    assert a1.session_id is None
    assert a1.expires_at is None
    assert a2.user_id is not None
    assert a2.session_id is None
    assert a2.expires_at is None

    # 4. Guest session cũ đã bị xóa
    guest_hash = hash_guest_token(guest_token)
    assert db_session.query(GuestSession).filter_by(token_hash=guest_hash).first() is None

    # 5. Replay claim với cùng token khách bị từ chối 400
    claim_again = client.post(
        "/api/v1/auth/claim-guest",
        headers=headers,
        json={"guest_session_token": guest_token},
    )
    assert claim_again.status_code == 400

    # 6. User có thể đọc các bài vừa nhận qua token tài khoản
    res_user_read = client.get(f"/api/v1/analyses/{id1}", headers=headers)
    assert res_user_read.status_code == 200

    # 7. Khách dùng token cũ đọc lại -> 404
    res_guest_read = client.get(
        f"/api/v1/analyses/{id1}",
        headers={"X-Guest-Session-Token": guest_token},
    )
    assert res_guest_read.status_code == 404


def test_cleanup_does_not_purge_claimed_analyses(client: TestClient, db_session):
    """Tiến trình cleanup không xóa analyses đã được user nhận quyền."""
    # Tạo phân tích khách
    res = client.post(
        "/api/v1/analyses",
        json={"text": "Tin tuyển dụng thử nghiệm dọn dẹp phiên"},
    )
    guest_token = res.json()["guest_session_token"]
    analysis_id = uuid.UUID(res.json()["id"])

    # User nhận quyền
    user_token = register_user(client, "keep_after_cleanup@example.com")
    client.post(
        "/api/v1/auth/claim-guest",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"guest_session_token": guest_token},
    )

    # Chạy cleanup ở thời điểm 3 ngày sau
    future = datetime.now(timezone.utc) + timedelta(days=3)
    purge_expired_sessions(db_session, reference_time=future)

    # Bản ghi phân tích của user vẫn còn nguyên vẹn
    record = db_session.query(Analysis).filter_by(id=analysis_id).first()
    assert record is not None
    assert record.user_id is not None


def test_saved_analyses_flow(client: TestClient):
    """Quy trình lưu, bỏ lưu và danh sách bài đã lưu của người dùng."""
    user1_token = register_user(client, "saver1@example.com")
    user2_token = register_user(client, "saver2@example.com")
    h1 = {"Authorization": f"Bearer {user1_token}"}
    h2 = {"Authorization": f"Bearer {user2_token}"}

    # User 1 tạo phân tích
    res = client.post(
        "/api/v1/analyses",
        headers=h1,
        json={"text": "Tin tuyển dụng của user 1 cần lưu lại"},
    )
    analysis_id = res.json()["id"]

    # User 2 cố lưu bài của User 1 -> 404
    res_steal = client.post(f"/api/v1/saved-analyses/{analysis_id}", headers=h2)
    assert res_steal.status_code == 404

    # User 1 lưu bài của chính mình -> 200/201
    res_save = client.post(f"/api/v1/saved-analyses/{analysis_id}", headers=h1)
    assert res_save.status_code in (200, 201)

    # Lấy danh sách bài đã lưu của User 1
    res_list = client.get("/api/v1/saved-analyses", headers=h1)
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert len(items) == 1
    assert items[0]["analysis_id"] == analysis_id

    # Danh sách của User 2 rỗng
    res_list2 = client.get("/api/v1/saved-analyses", headers=h2)
    assert res_list2.status_code == 200
    assert len(res_list2.json()["items"]) == 0

    # User 1 bỏ lưu
    res_unsave = client.delete(f"/api/v1/saved-analyses/{analysis_id}", headers=h1)
    assert res_unsave.status_code == 200

    # Lấy lại danh sách: 0 items
    res_empty = client.get("/api/v1/saved-analyses", headers=h1)
    assert len(res_empty.json()["items"]) == 0


def test_history_list_and_pagination(client: TestClient):
    """Lịch sử phân tích cá nhân có phân trang và đánh dấu is_saved."""
    token = register_user(client, "history@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created_ids = []
    for i in range(5):
        res = client.post(
            "/api/v1/analyses",
            headers=headers,
            json={"text": f"Tin tuyển dụng số {i}: yêu cầu văn phòng mức lương {10 + i} triệu."},
        )
        created_ids.append(res.json()["id"])

    # Lưu 1 bài
    client.post(f"/api/v1/saved-analyses/{created_ids[0]}", headers=headers)

    # Trang 1: limit 2
    res_p1 = client.get("/api/v1/analyses?page=1&page_size=2", headers=headers)
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert p1_data["total"] == 5
    assert len(p1_data["items"]) == 2
    assert p1_data["page"] == 1

    # Trang 3: limit 2 -> 1 item còn lại
    res_p3 = client.get("/api/v1/analyses?page=3&page_size=2", headers=headers)
    assert len(res_p3.json()["items"]) == 1

    # Lọc chỉ bài đã lưu
    res_saved_only = client.get("/api/v1/analyses?is_saved=true", headers=headers)
    assert res_saved_only.json()["total"] == 1
    assert res_saved_only.json()["items"][0]["id"] == created_ids[0]


def test_user_profile_update_and_password_change(client: TestClient):
    """Cập nhật tên hiển thị, đổi mật khẩu và thu hồi phiên toàn hệ thống."""
    token = register_user(client, "profile@example.com", name="Tên Ban Đầu")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Cập nhật tên
    patch_res = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "Tên Đã Đổi"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Tên Đã Đổi"

    # 2. Đổi mật khẩu với mật khẩu cũ sai -> 400
    bad_pwd_res = client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={
            "old_password": "wrong_old_password",
            "new_password": "new_secure_password_15ch",
        },
    )
    assert bad_pwd_res.status_code == 400

    # 3. Đổi mật khẩu với mật khẩu cũ đúng -> 200
    change_res = client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={
            "old_password": "secure_password_15_chars",
            "new_password": "new_secure_password_15ch",
        },
    )
    assert change_res.status_code == 200

    # 4. Phiên cũ bị thu hồi -> 401 khi gọi lại
    check_revoked = client.get("/api/v1/users/me", headers=headers)
    assert check_revoked.status_code == 401

    # 5. Đăng nhập lại với mật khẩu mới thành công
    login_new = client.post(
        "/api/v1/auth/login",
        json={
            "email": "profile@example.com",
            "password": "new_secure_password_15ch",
        },
    )
    assert login_new.status_code == 200
    new_token = login_new.json()["access_token"]
    assert client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200


def test_user_stats(client: TestClient):
    """Thống kê cá nhân trả về tổng phân tích, số bài đã lưu và phân bổ rủi ro."""
    token = register_user(client, "stats@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo 2 phân tích
    res1 = client.post(
        "/api/v1/analyses",
        headers=headers,
        json={"text": "Yêu cầu đặt cọc tiền phí hồ sơ 300k trước khi phỏng vấn"},
    )
    client.post(
        "/api/v1/analyses",
        headers=headers,
        json={"text": "Công ty TNHH Phần Mềm Tuyển dụng kỹ sư AI làm việc tại Hà Nội"},
    )
    client.post(f"/api/v1/saved-analyses/{res1.json()['id']}", headers=headers)

    res_stats = client.get("/api/v1/users/me/stats", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_analyses"] == 2
    assert stats["saved_analyses"] == 1
    assert isinstance(stats["risk_distribution"], dict)
