"""Test suite for R4.3 Admin Employer Curation, Detection Rules Management, and Statistics."""

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
from app.models.indicators import RiskIndicator
from app.models.reports import Report
from app.models.users import Role, User
from app.models.verifications import VerifiedEmployer


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

    # Seed initial rule
    rule = RiskIndicator(
        id=uuid.uuid4(),
        code="RULE_UPFRONT_FEE",
        name="Phí tuyển dụng trước",
        description="Thu phí trước",
        explanation_vi="Không thu phí",
        weight=35,
        enabled=True,
    )
    session.add(rule)
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


def create_admin_token(client: TestClient, email: str = "admin_mgmt@example.com") -> str:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "secure_password_15_chars",
            "full_name": "Admin Management",
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


def test_admin_manage_employers(client: TestClient):
    """Admin tạo, xem danh sách và cập nhật thông tin nhà tuyển dụng trong kho nguồn."""
    token = create_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo employer mới
    create_res = client.post(
        "/api/v1/admin/employers",
        json={"legal_name": "Công ty TNHH Phần mềm Mẫu", "tax_id": "0123456789"},
        headers=headers,
    )
    assert create_res.status_code == 201
    emp_data = create_res.json()
    emp_id = emp_data["id"]
    assert emp_data["legal_name"] == "Công ty TNHH Phần mềm Mẫu"
    assert emp_data["tax_id"] == "0123456789"
    assert emp_data["is_active"] is True

    # Tạo trùng tax_id -> 400
    dup_res = client.post(
        "/api/v1/admin/employers",
        json={"legal_name": "Công ty Khác", "tax_id": "0123456789"},
        headers=headers,
    )
    assert dup_res.status_code == 400

    # Cập nhật tên employer
    patch_res = client.patch(
        f"/api/v1/admin/employers/{emp_id}",
        json={"legal_name": "Công ty Cổ phần Phần mềm Mẫu Đổi Tên", "is_active": False},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["legal_name"] == "Công ty Cổ phần Phần mềm Mẫu Đổi Tên"
    assert patch_res.json()["is_active"] is False

    # Thêm nguồn và claim
    src_res = client.post(
        f"/api/v1/admin/employers/{emp_id}/sources",
        json={
            "url": "https://example.com/tuyen-dung",
            "label_vi": "Trang tuyển dụng chính thức",
            "evidence_excerpt_vi": "Email liên hệ chính thức hr@example.com",
        },
        headers=headers,
    )
    assert src_res.status_code == 201

    claim_res = client.post(
        f"/api/v1/admin/employers/{emp_id}/claims",
        json={
            "source_id": src_res.json()["id"],
            "field": "contact_email",
            "value": "hr@example.com",
            "assertion": "supports",
        },
        headers=headers,
    )
    assert claim_res.status_code == 201

    # Xem danh sách
    list_res = client.get("/api/v1/admin/employers", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["items"][0]["sources_count"] == 1


def test_admin_manage_rules(client: TestClient):
    """Admin xem danh sách và cập nhật bật/tắt, trọng số của quy tắc phát hiện."""
    token = create_admin_token(client, "admin_rules@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Danh sách rules
    list_res = client.get("/api/v1/admin/rules", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) >= 1
    assert any(r["code"] == "RULE_UPFRONT_FEE" for r in items)

    # Cập nhật rule: tắt và đổi trọng số
    patch_res = client.patch(
        "/api/v1/admin/rules/RULE_UPFRONT_FEE",
        json={"enabled": False, "weight": 50},
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated_rule = patch_res.json()
    assert updated_rule["enabled"] is False
    assert updated_rule["weight"] == 50

    # Rule không tồn tại -> 404
    not_found_res = client.patch(
        "/api/v1/admin/rules/NON_EXISTENT_RULE",
        json={"enabled": True},
        headers=headers,
    )
    assert not_found_res.status_code == 404


def test_admin_statistics_dashboard(client: TestClient, db_session):
    """Admin lấy các chỉ số thống kê tổng hợp của toàn hệ thống."""
    token = create_admin_token(client, "admin_stats@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo 1 report trong DB
    user = db_session.query(User).filter_by(email="admin_stats@example.com").first()
    rep = Report(
        reporter_id=user.id,
        reason="Nhiệm vụ lừa đảo",
        description="Nạp tiền rồi mất liên lạc",
        status="pending",
    )
    db_session.add(rep)

    # Tạo 1 analysis trong DB
    analysis = Analysis(
        user_id=user.id,
        raw_text="Tin tuyển dụng mẫu",
        risk_label_vi="Rủi ro cao",
        verification_label_vi="Chưa xác minh",
        finding_vi="Có dấu hiệu rủi ro cao",
        job={},
        indicators=[],
        evidence={},
        actions_vi=[],
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(analysis)
    db_session.commit()

    stats_res = client.get("/api/v1/admin/statistics", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_users"] >= 1
    assert stats["total_analyses"] >= 1
    assert stats["total_reports"] >= 1
    assert stats["pending_reports"] >= 1
    assert stats["risk_distribution"].get("Rủi ro cao", 0) >= 1
    assert stats["report_status_distribution"].get("pending", 0) >= 1


def test_clear_employer_tax_id(client):
    headers = {"Authorization": f"Bearer {create_admin_token(client)}"}
    employer = client.post("/api/v1/admin/employers", headers=headers, json={"legal_name": "Employer", "tax_id": "1234567890"}).json()
    response = client.patch(f"/api/v1/admin/employers/{employer['id']}", headers=headers, json={"tax_id": None})
    assert response.status_code == 200
    assert response.json()["tax_id"] is None


def test_source_validation_and_explicit_bank_claim(client):
    headers = {"Authorization": f"Bearer {create_admin_token(client)}"}
    employer = client.post("/api/v1/admin/employers", headers=headers, json={"legal_name": "Bank Employer"}).json()
    base = f"/api/v1/admin/employers/{employer['id']}"
    for url in ("https://example.com/?token=private", "https://user:pass@example.com", "http://127.0.0.1", "javascript:alert(1)"):
        response = client.post(base + "/sources", headers=headers, json={"url": url, "label_vi": "Source", "evidence_excerpt_vi": "Reviewed evidence"})
        assert response.status_code == 422
    first = client.post(base + "/sources", headers=headers, json={"url": "https://example.com/old", "label_vi": "Old", "evidence_excerpt_vi": "Old evidence"}).json()
    second = client.post(base + "/sources", headers=headers, json={"url": "https://example.com/new", "label_vi": "New", "evidence_excerpt_vi": "Bank details checked, private values omitted"}).json()
    bank = {"account_number": "123456789", "bank_name": "Example Bank", "account_holder": "Example Holder"}
    response = client.post(base + "/claims", headers=headers, json={"source_id": second["id"], "field": "bank_account", "value": bank})
    assert response.status_code == 201
    checked = client.post("/api/v1/verifications", json={"bank_account": bank}).json()
    assert checked["verification_label_vi"] == "Khớp nguồn đã xác minh"
    assert [s["id"] for s in checked["matched_sources"]] == [second["id"]]
    response = client.post(base + "/claims", headers=headers, json={"source_id": first["id"], "field": "contact_email", "value": "invalid"})
    assert response.status_code == 422


def test_disabled_rule_is_not_detected(client):
    headers = {"Authorization": f"Bearer {create_admin_token(client)}"}
    text = "Yêu cầu đóng phí hồ sơ 300.000 đồng trước khi nhận việc."
    before = client.post("/api/v1/analyses", headers=headers, json={"text": text}).json()
    assert any(i["rule_id"] == "RULE_UPFRONT_FEE" for i in before["indicators"])
    client.patch("/api/v1/admin/rules/RULE_UPFRONT_FEE", headers=headers, json={"enabled": False})
    after = client.post("/api/v1/analyses", headers=headers, json={"text": text}).json()
    assert all(i["rule_id"] != "RULE_UPFRONT_FEE" for i in after["indicators"])


def test_rule_weight_changes_priority_and_is_snapshotted(client, db_session):
    from app.services.analysis import perform_text_analysis
    from types import SimpleNamespace
    settings = {"RULE_UPFRONT_FEE": SimpleNamespace(enabled=True, weight=10, explanation_vi="Fee priority"), "RULE_SENSITIVE_DATA": SimpleNamespace(enabled=True, weight=90, explanation_vi="Sensitive priority")}
    text = "Yêu cầu đóng phí hồ sơ 300.000 đồng trước khi nhận việc. Yêu cầu gửi ảnh hai mặt CCCD."
    result = perform_text_analysis(text, rule_settings=settings)
    indicators = result[1]
    assert {i.rule_id for i in indicators} >= set(settings)
    assert indicators[0].rule_id == "RULE_SENSITIVE_DATA"
    assert indicators[0].weight == 90
    settings["RULE_UPFRONT_FEE"].weight = 100
    changed = perform_text_analysis(text, rule_settings=settings)[1]
    assert changed[0].rule_id == "RULE_UPFRONT_FEE"
    assert changed[0].weight == 100
    assert indicators[0].weight == 90
