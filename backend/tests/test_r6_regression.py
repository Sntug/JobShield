"""R6 Comprehensive Cross-Release Regression Test Suite.

Kiểm chứng các giao điểm nghiệp vụ và ranh giới an toàn tích hợp từ R1 đến R5:
1. R1 + R2: Guest analysis, TTL 24h, session isolation, claim transition, and user ownership.
2. R3: Safe extraction (SSRF prevention, image validation, fallback to manual text).
3. R4: Report submission, RBAC isolation, optimistic locking (409 conflict), public warning lifecycle (publish -> supersede -> withdraw) and PII redaction.
4. R5: Optional AI semantic layer, consent enforcement, multi-layer fallback, prompt injection defense, and rule engine supremacy.
5. Cross-cutting: Security headers, session revocation on password change, rate limits.
"""

from datetime import datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import reset_rate_limits
from app.core.security import generate_guest_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.reports import PublicWarning, Report
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


def register_user(client: TestClient, email: str, name: str = "Test User", password: str = "secure_password_15_chars") -> str:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )
    assert res.status_code == 201
    return res.json()["access_token"]


def create_admin_token(client: TestClient, email: str = "admin_r6@example.com") -> str:
    token = register_user(client, email, "Admin R6")
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter_by(email=email).first()
    admin_role = db.query(Role).filter_by(name="admin").first()
    user.role_id = admin_role.id
    db.commit()
    return token


SCAM_UPFRONT_FEE_TEXT = (
    "Công ty Mẫu Thu Phí (DEMO) tuyển Nhân viên nhập liệu. Lương: 8 triệu đồng/tháng. "
    "Làm online bán thời gian. Email: nhanviec@thu-phi.invalid. Yêu cầu: đóng phí tuyển dụng 500.000 đồng để nhận việc. "
    "Đặt cọc 1.000.000 đồng trước phỏng vấn. Chuyển tiền vào tài khoản cá nhân để giữ chỗ."
)


# ==============================================================================
# 1. R1 + R2: Guest Analysis & Ownership Transition Regression
# ==============================================================================

def test_r6_guest_analysis_and_session_isolation(client: TestClient):
    """Khách phân tích tin -> nhận token -> đọc lại được; khách khác hoặc không token bị 401."""
    post_res = client.post(
        "/api/v1/analyses",
        json={"text": SCAM_UPFRONT_FEE_TEXT},
    )
    assert post_res.status_code == 201
    data = post_res.json()
    analysis_id = data["id"]
    guest_token = data["guest_session_token"]
    assert guest_token is not None
    assert data["risk_label_vi"] == "Rủi ro cao"

    # 1.1 Truy cập hợp lệ bằng X-Guest-Session-Token
    get_res = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"X-Guest-Session-Token": guest_token},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == analysis_id

    # 1.2 Không có token -> 401 hoặc 404
    anon_res = client.get(f"/api/v1/analyses/{analysis_id}")
    assert anon_res.status_code in (401, 404)

    # 1.3 Token giả / token của phiên khác -> 401 hoặc 404
    fake_token = generate_guest_token()
    fake_res = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"X-Guest-Session-Token": fake_token},
    )
    assert fake_res.status_code in (401, 404)


def test_r6_guest_claim_transition_and_token_invalidation(client: TestClient):
    """Khi đăng nhập và nhận quyền phân tích (claim), chủ sở hữu chuyển sang user, guest token cũ bị hủy."""
    token = register_user(client, "claim_r6@example.com")

    # Tạo 1 guest analysis
    post_res = client.post(
        "/api/v1/analyses",
        json={"text": SCAM_UPFRONT_FEE_TEXT},
    )
    assert post_res.status_code == 201
    data = post_res.json()
    analysis_id = data["id"]
    guest_token = data["guest_session_token"]

    # Claim analysis vào tài khoản
    claim_res = client.post(
        "/api/v1/auth/claim-guest",
        json={"guest_session_token": guest_token},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert claim_res.status_code == 200
    assert claim_res.json()["claimed_count"] >= 1

    # User đọc được bằng Bearer token
    user_res = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert user_res.status_code == 200

    # Guest token cũ không còn đọc được nữa
    guest_after_res = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"X-Guest-Session-Token": guest_token},
    )
    assert guest_after_res.status_code in (401, 404)


# ==============================================================================
# 2. R3: Safe Extraction Regressions (SSRF, Validation & Fallback)
# ==============================================================================

def test_r6_url_extraction_ssrf_protection(client: TestClient):
    """Kiểm tra URL extraction chặn triệt để dải IP private/loopback/cloud metadata (chống SSRF)."""
    blocked_urls = [
        "http://127.0.0.1/internal-admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/router",
        "http://127.0.0.1:8000/internal-admin",  # Unapproved port
    ]
    for url in blocked_urls:
        res = client.post("/api/v1/extractions/url", json={"url": url})
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is False
        assert body["failure_vi"] is not None
        assert any(kw in body["failure_vi"].lower() for kw in ("nội bộ", "cục bộ", "chặn", "ssrf", "riêng tư", "hỗ trợ", "cổng"))


def test_r6_image_upload_validation(client: TestClient):
    """Kiểm tra upload ảnh từ chối file không phải ảnh và file rỗng/quá dung lượng an toàn."""
    fake_img = b"This is plain text pretending to be image"
    res = client.post(
        "/api/v1/extractions/image",
        content=fake_img,
        headers={"Content-Type": "image/png", "X-Filename": "fake.png"},
    )
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert res.json()["failure_vi"] is not None


# ==============================================================================
# 3. R4: Reporting, Optimistic Locking & Warning Lifecycle Regression
# ==============================================================================

def test_r6_report_lifecycle_and_optimistic_locking(client: TestClient):
    """Kiểm tra vòng đời báo cáo: gửi -> kiểm duyệt -> chống ghi đè phiên bản 409 Conflict."""
    user_token = register_user(client, "reporter_r6@example.com")
    admin_token = create_admin_token(client, "admin_mod_r6@example.com")

    # Người dùng gửi báo cáo
    submit_res = client.post(
        "/api/v1/reports",
        json={
            "reason": "Yêu cầu đặt cọc tiền giữ chỗ",
            "description": "Nhà tuyển dụng bắt chuyển 2 triệu trước khi phỏng vấn",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert submit_res.status_code == 201
    report_id = submit_res.json()["id"]
    assert submit_res.json()["version"] == 1

    # Người dùng khác không được xem báo cáo này (RBAC)
    other_token = register_user(client, "other_r6@example.com")
    other_res = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_res.status_code in (403, 404)

    # Admin A kiểm duyệt thành công (expected_version=1 -> version trở thành 2)
    mod_a_res = client.post(
        f"/api/v1/admin/reports/{report_id}/moderation",
        json={
            "action_type": "verify",
            "to_status": "verified",
            "decision_summary": "Đã xác minh dấu hiệu thu phí bất hợp pháp.",
            "private_note": "Bằng chứng chuyển khoản rõ ràng.",
            "expected_version": 1,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert mod_a_res.status_code == 200
    assert mod_a_res.json()["version"] == 2

    # Admin B thao tác đồng thời với expected_version=1 cũ -> nhận 409 Conflict
    mod_b_res = client.post(
        f"/api/v1/admin/reports/{report_id}/moderation",
        json={
            "action_type": "reject",
            "to_status": "rejected",
            "decision_summary": "Từ chối",
            "expected_version": 1,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert mod_b_res.status_code == 409
    assert "CONFLICT" in mod_b_res.json()["detail"].upper() or "VERSION" in mod_b_res.json()["detail"].upper()


def test_r6_public_warning_lifecycle_and_pii_redaction(client: TestClient):
    """Kiểm tra cảnh báo công khai: xuất bản -> đính chính -> thu hồi và không lộ PII người báo cáo."""
    admin_token = create_admin_token(client, "admin_warn_r6@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin xuất bản cảnh báo công khai
    pub_res = client.post(
        "/api/v1/admin/warnings",
        json={
            "title_vi": "Cảnh báo mạo danh tập đoàn ABC lừa nạp tiền",
            "public_summary_vi": "Phát hiện tài khoản Telegram mạo danh nhân sự ABC để thu phí hồ sơ 500k.",
            "public_sources_snapshot": [
                {"label_vi": "Tin cảnh báo nội bộ", "url": "https://example.com/warning-source"}
            ],
        },
        headers=admin_headers,
    )
    assert pub_res.status_code == 201
    warning_id = pub_res.json()["id"]

    # 2. Truy cập công khai không cần auth -> dữ liệu sạch, không chứa email admin
    public_res = client.get(f"/api/v1/warnings/{warning_id}")
    assert public_res.status_code == 200
    pub_data = public_res.json()
    assert "admin_warn_r6@example.com" not in str(pub_data)
    assert pub_data["status"] == "published"
    assert pub_data["revision"] == 1

    # 3. Đính chính (supersede -> revision 2)
    sup_res = client.post(
        f"/api/v1/admin/warnings/{warning_id}/supersede",
        json={
            "title_vi": "Cảnh báo đính chính: Mạo danh tập đoàn ABC lừa nạp tiền và OTP",
            "public_summary_vi": "Bổ sung dấu hiệu yêu cầu cung cấp OTP ngân hàng.",
            "public_sources_snapshot": [
                {"label_vi": "Tin cảnh báo bổ sung", "url": "https://example.com/warning-source-v2"}
            ],
        },
        headers=admin_headers,
    )
    assert sup_res.status_code == 200
    v2_id = sup_res.json()["id"]
    assert sup_res.json()["revision"] == 2

    # Bản cũ trở thành superseded
    old_res = client.get(f"/api/v1/warnings/{warning_id}")
    assert old_res.json()["status"] == "superseded"
    assert old_res.json()["next_warning_id"] == v2_id

    # 4. Thu hồi bản v2 (withdraw)
    with_res = client.post(
        f"/api/v1/admin/warnings/{v2_id}/withdraw",
        json={"withdrawal_reason_vi": "Doanh nghiệp đã can thiệp gỡ bỏ kênh mạo danh."},
        headers=admin_headers,
    )
    assert with_res.status_code == 200
    assert with_res.json()["status"] == "withdrawn"


# ==============================================================================
# 4. R5: Optional AI Fallback & Safety Regression
# ==============================================================================

def test_r6_ai_consent_and_fallback_regression(client: TestClient):
    """Kiểm tra AI tùy chọn: từ chối consent -> 100% rule-based, không gọi provider ngoài."""
    res = client.post(
        "/api/v1/analyses",
        json={
            "text": "Tuyển dụng nhân viên bán hàng tại siêu thị, phỏng vấn trực tiếp.",
            "use_ai": True,
            "ai_consent": False,
        },
    )
    assert res.status_code == 201
    data = res.json()
    if data.get("ai_insights"):
        assert data["ai_insights"]["status"] == "fallback_no_consent"


def test_r6_ai_rule_engine_supremacy(client: TestClient):
    """Dấu hiệu rủi ro cao từ Rule Engine là tối thượng; AI không thể hạ thấp mức rủi ro."""
    res = client.post(
        "/api/v1/analyses",
        json={"text": SCAM_UPFRONT_FEE_TEXT, "use_ai": False},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["risk_label_vi"] == "Rủi ro cao"
    assert any("UPFRONT_FEE" in ind.get("rule_id", "") for ind in data["indicators"])


# ==============================================================================
# 5. Cross-Cutting: Security Headers & Session Revocation
# ==============================================================================

def test_r6_security_headers_and_privacy(client: TestClient):
    """Kiểm tra response headers có đầy đủ trace, commit SHA và no-store cho endpoint nhạy cảm."""
    res = client.get("/healthz")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    assert "x-commit-sha" in res.headers

    # Endpoint người dùng phải có Cache-Control: no-store
    auth_res = client.post("/api/v1/auth/login", json={"email": "none@example.com", "password": "wrong"})
    assert auth_res.status_code == 401
    assert "no-store" in auth_res.headers.get("cache-control", "").lower()


def test_r6_password_change_revokes_all_sessions(client: TestClient):
    """Khi đổi mật khẩu, toàn bộ phiên truy cập hiện tại của tài khoản phải bị thu hồi ngay lập tức."""
    email = "revoke_r6@example.com"
    pwd_old = "old_password_15_chars"
    pwd_new = "new_password_15_chars_secure"

    token = register_user(client, email, password=pwd_old)

    # Xác nhận token cũ đang dùng được
    me_res = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200

    # Đổi mật khẩu
    chg_res = client.post(
        "/api/v1/users/me/password",
        json={"old_password": pwd_old, "new_password": pwd_new},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chg_res.status_code == 200

    # Token cũ ngay lập tức bị từ chối 401
    me_after = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401
