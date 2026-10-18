"""Comprehensive test suite for R1.1 Text Analysis and Guest Sessions."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import reset_rate_limits
from app.core.security import generate_guest_token, hash_guest_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analyses import Analysis
from app.models.guest_sessions import GuestSession
from app.services.analysis import perform_text_analysis
from app.services.rule_engine import detect_indicators
from app.cli.cleanup import purge_expired_sessions


# Database test độc lập (SQLite in-memory thread-safe cho TestClient)
@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    reset_rate_limits()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    reset_rate_limits()


@pytest.fixture
def fixture_cases():
    fixture_path = Path(__file__).parent / "fixtures/recruitment_cases.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)["cases"]


def test_post_analysis_without_token_issues_session(client):
    """POST không kèm token -> tạo phiên mới, trả 201 kèm guest_session_token."""
    response = client.post(
        "/api/v1/analyses",
        json={"text": "Công ty Mẫu A tuyển nhân viên hỗ trợ, lương 10 triệu/tháng."},
    )
    assert response.status_code == 201
    assert response.headers.get("Cache-Control") == "no-store"
    data = response.json()
    assert data["id"]
    assert data["guest_session_token"]
    assert len(data["guest_session_token"]) >= 40
    assert data["risk_label_vi"]
    assert data["verification_label_vi"]


def test_post_analysis_with_empty_token_returns_401(client):
    """POST kèm header rỗng -> trả 401 SESSION_INVALID, không tự cấp phiên mới."""
    response = client.post(
        "/api/v1/analyses",
        headers={"X-Guest-Session-Token": ""},
        json={"text": "Công ty Mẫu A tuyển nhân viên hỗ trợ."},
    )
    assert response.status_code == 401
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json()["detail"] == "SESSION_INVALID"


def test_post_analysis_with_invalid_token_returns_401(client):
    """POST kèm token không tồn tại -> trả 401 SESSION_INVALID."""
    response = client.post(
        "/api/v1/analyses",
        headers={"X-Guest-Session-Token": "invalid_dummy_token_12345"},
        json={"text": "Công ty Mẫu A tuyển nhân viên hỗ trợ."},
    )
    assert response.status_code == 401
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json()["detail"] == "SESSION_INVALID"


def test_post_analysis_with_valid_token_reuses_session(client):
    """POST kèm token hợp lệ -> gán vào phiên đã có, response không trả lại token."""
    # 1. Tạo phiên đầu tiên
    res1 = client.post(
        "/api/v1/analyses",
        json={"text": "Công ty Mẫu A tuyển nhân viên hỗ trợ lần 1."},
    )
    token = res1.json()["guest_session_token"]

    # 2. Gửi tiếp bài thứ hai với cùng token
    res2 = client.post(
        "/api/v1/analyses",
        headers={"X-Guest-Session-Token": token},
        json={"text": "Công ty Mẫu A tuyển nhân viên hỗ trợ lần 2."},
    )
    assert res2.status_code == 201
    assert res2.json()["guest_session_token"] is None
    assert res2.json()["expires_at"] == res1.json()["expires_at"]


def test_post_validation_sanitizes_errors_without_echoing_input(client):
    """Lỗi 422 không được echo lại chuỗi văn bản đầu vào để bảo vệ quyền riêng tư."""
    secret_text = "   "
    response = client.post("/api/v1/analyses", json={"text": secret_text})
    assert response.status_code == 422
    assert response.headers.get("Cache-Control") == "no-store"
    body = response.json()
    assert "input" not in str(body)

    # Thử với chuỗi vượt quá 10.000 ký tự
    long_secret = "A" * 10001
    response = client.post("/api/v1/analyses", json={"text": long_secret})
    assert response.status_code == 422
    assert "input" not in str(response.json())


def test_get_analysis_access_control(client):
    """GET chỉ trả 200 khi đúng token cùng phiên; sai/thiếu token trả 404 uniform."""
    res1 = client.post(
        "/api/v1/analyses",
        json={"text": "Công ty Mẫu A tuyển Tester lương 10 triệu."},
    )
    analysis_id = res1.json()["id"]
    valid_token = res1.json()["guest_session_token"]

    # Đúng token -> 200
    res_get = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"X-Guest-Session-Token": valid_token},
    )
    assert res_get.status_code == 200
    assert res_get.headers.get("Cache-Control") == "no-store"
    assert res_get.json()["id"] == analysis_id
    assert res_get.json()["guest_session_token"] is None

    # Thiếu header -> 404
    res_no_header = client.get(f"/api/v1/analyses/{analysis_id}")
    assert res_no_header.status_code == 404
    assert res_no_header.headers.get("Cache-Control") == "no-store"

    # Sai token -> 404
    res_bad_token = client.get(
        f"/api/v1/analyses/{analysis_id}",
        headers={"X-Guest-Session-Token": "different_token_123"},
    )
    assert res_bad_token.status_code == 404
    assert res_bad_token.headers.get("Cache-Control") == "no-store"

    # Non-existent ID -> 404
    assert (
        client.get(
            f"/api/v1/analyses/{uuid.uuid4()}",
            headers={"X-Guest-Session-Token": valid_token},
        ).status_code
        == 404
    )


def test_expired_session_returns_401_on_post_and_404_on_get(client, db_session):
    """Phiên hết hạn -> POST trả 401, GET trả 404."""
    # Tạo phiên đã hết hạn trong quá khứ
    past = datetime.now(timezone.utc) - timedelta(hours=25)
    token = generate_guest_token()
    token_hash = hash_guest_token(token)
    session = GuestSession(
        token_hash=token_hash,
        created_at=past,
        expires_at=past + timedelta(hours=24),
    )
    db_session.add(session)
    db_session.flush()

    analysis = Analysis(
        id=uuid.uuid4(),
        session_id=session.id,
        raw_text="Tin quá hạn",
        risk_label_vi="Ít dấu hiệu rủi ro",
        verification_label_vi="Chưa xác minh",
        finding_vi="finding",
        job={},
        indicators=[],
        evidence={},
        actions_vi=[],
        engine_version="0.1.0",
        rules_version="2026.10",
        created_at=past,
        expires_at=session.expires_at,
    )
    db_session.add(analysis)
    db_session.commit()

    # POST với token hết hạn -> 401
    res_post = client.post(
        "/api/v1/analyses",
        headers={"X-Guest-Session-Token": token},
        json={"text": "Tin tuyển dụng mới"},
    )
    assert res_post.status_code == 401
    assert res_post.headers.get("Cache-Control") == "no-store"
    assert res_post.json()["detail"] == "SESSION_INVALID"

    # GET với token hết hạn -> 404
    res_get = client.get(
        f"/api/v1/analyses/{analysis.id}",
        headers={"X-Guest-Session-Token": token},
    )
    assert res_get.status_code == 404
    assert res_get.headers.get("Cache-Control") == "no-store"


def test_rate_limiter_blocks_11th_request_and_ignores_spoofed_xff(client):
    """Rate limit 10 req/phút; request thứ 11 trả 429; spoofing XFF không bypass được."""
    reset_rate_limits()
    payload = {"text": "Tin tuyển dụng bình thường để thử rate limit."}

    for i in range(10):
        # Cố tình đổi header X-Forwarded-For mỗi lần để thử bypass
        res = client.post(
            "/api/v1/analyses",
            headers={"X-Forwarded-For": f"192.168.1.{i+1}"},
            json=payload,
        )
        assert res.status_code == 201

    # Request thứ 11 -> 429
    res_blocked = client.post(
        "/api/v1/analyses",
        headers={"X-Forwarded-For": "192.168.1.99"},
        json=payload,
    )
    assert res_blocked.status_code == 429
    assert "Retry-After" in res_blocked.headers
    assert res_blocked.headers.get("Cache-Control") == "no-store"


def test_cleanup_purges_expired_and_cascades_analyses(db_session):
    """Hàm dọn dẹp xóa các phiên quá hạn và cascade xóa các analyses liên quan."""
    now = datetime.now(timezone.utc)

    # 1. Phiên đã hết hạn
    expired_token = generate_guest_token()
    s_expired = GuestSession(
        token_hash=hash_guest_token(expired_token),
        created_at=now - timedelta(hours=25),
        expires_at=now - timedelta(hours=1),
    )
    db_session.add(s_expired)
    db_session.flush()
    s_expired_id = s_expired.id

    a_expired = Analysis(
        id=uuid.uuid4(),
        session_id=s_expired_id,
        raw_text="Tin của phiên hết hạn",
        risk_label_vi="Ít dấu hiệu rủi ro",
        verification_label_vi="Chưa xác minh",
        finding_vi="finding",
        job={},
        indicators=[],
        evidence={},
        actions_vi=[],
        engine_version="0.1.0",
        rules_version="2026.10",
        created_at=now - timedelta(hours=25),
        expires_at=s_expired.expires_at,
    )
    db_session.add(a_expired)
    db_session.flush()
    a_expired_id = a_expired.id

    # 2. Phiên còn hạn
    active_token = generate_guest_token()
    s_active = GuestSession(
        token_hash=hash_guest_token(active_token),
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(s_active)
    db_session.flush()
    s_active_id = s_active.id

    a_active = Analysis(
        id=uuid.uuid4(),
        session_id=s_active_id,
        raw_text="Tin của phiên còn hạn",
        risk_label_vi="Ít dấu hiệu rủi ro",
        verification_label_vi="Chưa xác minh",
        finding_vi="finding",
        job={},
        indicators=[],
        evidence={},
        actions_vi=[],
        engine_version="0.1.0",
        rules_version="2026.10",
        created_at=now,
        expires_at=s_active.expires_at,
    )
    db_session.add(a_active)
    db_session.flush()
    a_active_id = a_active.id
    db_session.commit()

    # Thực hiện dọn dẹp
    deleted_sessions, deleted_analyses = purge_expired_sessions(db_session, reference_time=now)
    assert deleted_sessions == 1
    assert deleted_analyses == 1

    # Kiểm tra DB: s_expired và a_expired đã bị xóa; s_active và a_active vẫn còn
    assert db_session.query(GuestSession).filter_by(id=s_expired_id).first() is None
    assert db_session.query(Analysis).filter_by(id=a_expired_id).first() is None
    assert db_session.query(GuestSession).filter_by(id=s_active_id).first() is not None
    assert db_session.query(Analysis).filter_by(id=a_active_id).first() is not None


def test_regression_all_7_fixture_cases(fixture_cases):
    """Kiểm tra toàn bộ 7 tình huống văn bản với kết quả kỳ vọng."""
    for case in fixture_cases:
        if not case["input"]["text"]:
            continue
        cid = case["id"]
        text = case["input"]["text"]
        emp_records = case.get("employer_records", [])
        is_demo = case.get("is_demo", True)

        job, indicators, risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi = (
            perform_text_analysis(text=text, employer_records=emp_records, is_demo=is_demo)
        )

        exp = case["expected"]
        # So khớp 11 trường job
        for field, exp_val in exp["job"].items():
            actual_val = getattr(job, field)
            assert actual_val == exp_val, f"[{cid}] Field {field}: got {actual_val}, expected {exp_val}"

        # So khớp indicators
        assert len(indicators) == len(exp["indicators"]), f"[{cid}] Indicators count mismatch"
        for i, exp_ind in enumerate(exp["indicators"]):
            assert indicators[i].category_vi == exp_ind["category_vi"]
            assert indicators[i].matched_quote == exp_ind["matched_quote"]
            assert indicators[i].matched_quote in text

        # So khớp nhãn
        assert risk_label_vi == exp["risk_label_vi"], f"[{cid}] Risk label mismatch"
        assert verification_label_vi == exp["verification_label_vi"], f"[{cid}] Verification mismatch"
        assert evidence.missing_vi == exp["evidence"]["missing_vi"], f"[{cid}] Missing items mismatch"


def test_counter_example_1_legitimate_intro_is_not_impersonation():
    """CE1: Giới thiệu phòng tuyển dụng với email cùng domain không bị coi là mạo danh."""
    text = (
        "Công ty Bình An tuyển Tester. Lương: 8 triệu đồng/tháng. Email: hr@binhan.example. "
        "Chúng tôi là phòng tuyển dụng Công ty Bình An, chỉ nhận hồ sơ tại hr@binhan.example."
    )
    job, indicators, risk_label_vi, verification_label_vi, _, _, _ = perform_text_analysis(text)
    assert not any(ind.rule_id == "RULE_IMPERSONATION" for ind in indicators)
    assert risk_label_vi == "Ít dấu hiệu rủi ro"


def test_counter_example_2_otp_via_zalo_triggers_sensitive_data():
    """CE2: Yêu cầu gửi OTP qua Zalo phải kích hoạt RULE_SENSITIVE_DATA."""
    text = (
        "Công ty Bình An tuyển Tester. Lương: 8 triệu đồng/tháng. Email: hr@binhan.example. "
        "Gửi mã OTP ngân hàng cho người tuyển dụng qua Zalo."
    )
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"


def test_counter_example_3_bare_text_lacking_salary_and_contact():
    """CE3: Tin chỉ có tên công ty và vị trí nhưng thiếu lương và liên hệ phải là Không đủ thông tin."""
    text = "Công ty Bình An tuyển Tester."
    job, indicators, risk_label_vi, verification_label_vi, _, evidence, _ = perform_text_analysis(text)
    assert risk_label_vi == "Không đủ thông tin"
    assert "Mức lương" in evidence.missing_vi
    assert "Email/domain hoặc kênh tuyển dụng đối chiếu được" in evidence.missing_vi


def test_counter_example_4_deposit_with_verified_employer_keeps_high_risk():
    """CE4: Dù nguồn employer khớp xác minh, nếu có yêu cầu đặt cọc thì risk vẫn luôn là Rủi ro cao."""
    text = (
        "Công ty Mẫu A (DEMO) tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. "
        "Email: tuyendung@mau-a.example. Website: https://mau-a.example/tuyen-dung. "
        "Đặt cọc 1.000.000 đồng trước phỏng vấn."
    )
    emp_records = [{
        "name": "Công ty Mẫu A (DEMO)",
        "official_domains": ["mau-a.example"],
        "official_contacts": ["tuyendung@mau-a.example"],
        "sources": [{"id": "demo-source-a", "url": "https://mau-a.example/tuyen-dung", "label_vi": "DEMO"}]
    }]
    job, indicators, risk_label_vi, verification_label_vi, _, _, _ = perform_text_analysis(
        text, employer_records=emp_records, is_demo=True
    )
    assert any(ind.rule_id == "RULE_DEPOSIT_BEFORE_INTERVIEW" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"
    assert verification_label_vi == "Khớp nguồn đã xác minh"


def test_counter_example_5_negated_sensitive_data_not_false_positive():
    """CE5: Mệnh đề phủ định 'Không Gửi ảnh hai mặt CCCD...' không tạo false-positive."""
    text = (
        "Công ty Bình An tuyển Tester. Lương: 8 triệu đồng/tháng. Email: hr@binhan.example. "
        "Không Gửi ảnh hai mặt CCCD và mã OTP ngân hàng qua chat trước khi nhận việc."
    )
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert not any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)


def test_regression_local_negation_contrasted_clause():
    """Phủ định cục bộ ở vế đầu không triệt tiêu dấu hiệu cảnh báo ở vế sau liên từ nhưng."""
    text = "Không thu phí nhưng yêu cầu gửi mã OTP ngân hàng qua Zalo."
    indicators = detect_indicators(text)
    assert len(indicators) == 1
    assert indicators[0].rule_id == "RULE_SENSITIVE_DATA"
    assert indicators[0].matched_quote == "yêu cầu gửi mã OTP ngân hàng qua Zalo"


def test_regression_upfront_fee_flexible_tail():
    """Luật phí tuyển dụng nhận diện biến thể đuôi 'trước phỏng vấn' thay vì chỉ 'để nhận việc'."""
    text = "Yêu cầu nộp phí tuyển dụng 500.000 đồng trước phỏng vấn."
    indicators = detect_indicators(text)
    assert len(indicators) == 1
    assert indicators[0].rule_id == "RULE_UPFRONT_FEE"
    assert indicators[0].matched_quote == "Yêu cầu nộp phí tuyển dụng 500.000 đồng trước phỏng vấn"


def test_regression_claimed_intro_without_employer_records_not_impersonation():
    """Không tự suy ra mạo danh từ tên công ty vs domain email khi chưa có employer_records."""
    text = "Chúng tôi là phòng tuyển dụng Công ty Bình An, chỉ nhận hồ sơ tại hr@gmail.com."
    job, indicators, risk_label_vi, verification_label_vi, _, _, _ = perform_text_analysis(
        text, employer_records=None
    )
    assert not any(ind.rule_id == "RULE_IMPERSONATION" for ind in indicators)
    assert verification_label_vi == "Chưa xác minh"


def test_regression_same_name_insufficient_contact_keeps_high_risk_on_indicator():
    """Khi có indicator thì risk luôn là Rủi ro cao, không bị hạ thành Không đủ thông tin dù trùng tên thiếu liên hệ."""
    text = (
        "Công ty Bình An tuyển Tester. Lương: 8 triệu đồng/tháng. "
        "Đặt cọc 1.000.000 đồng trước phỏng vấn."
    )
    emp_records = [{
        "name": "Công ty Bình An",
        "official_domains": ["binhan.example"],
        "sources": []
    }]
    job, indicators, risk_label_vi, verification_label_vi, _, _, _ = perform_text_analysis(
        text, employer_records=emp_records
    )
    assert any(ind.rule_id == "RULE_DEPOSIT_BEFORE_INTERVIEW" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"
    assert verification_label_vi == "Chưa xác minh"


def test_regression_unrelated_website_conflict_not_matched_and_empty_sources():
    """Website khác official_domains của nguồn phải là Thông tin xung đột, không được coi là Khớp nguồn và sources trống."""
    text = (
        "Công ty Bình An tuyển Tester. Lương: 8 triệu đồng/tháng. "
        "Website: https://unrelated.example."
    )
    emp_records = [{
        "name": "Công ty Bình An",
        "official_domains": ["binhan.example"],
        "sources": []
    }]
    job, indicators, risk_label_vi, verification_label_vi, _, evidence, _ = perform_text_analysis(
        text, employer_records=emp_records
    )
    assert verification_label_vi == "Thông tin xung đột"
    assert evidence.matched_sources == []


def test_clause_negation_does_not_mask_otp_demand():
    """Mệnh đề phủ định (không thu phí) không che giấu chỉ dấu OTP ở mệnh đề sau dấu phẩy."""
    text = "Không thu phí, yêu cầu gửi mã OTP ngân hàng qua Zalo."
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"


def test_lowercase_sentence_after_dot_detects_otp():
    """Dấu chấm trước chữ thường vẫn tách câu và nhận diện chỉ dấu OTP, trả Rủi ro cao."""
    text = (
        "Công ty ABC tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. "
        "Email: hr@abc.example. không thu phí. yêu cầu gửi mã OTP ngân hàng qua Zalo."
    )
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"


def test_explicit_negation_of_sensitive_data_not_flagged():
    """Mệnh đề cảnh báo không gửi mã OTP không bị đánh dấu nhầm thành rủi ro."""
    text = "Lưu ý an toàn: Tuyệt đối không gửi mã OTP, CCCD cho bất kỳ ai."
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert not any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)


def test_list_context_preserves_otp_demand():
    """Yêu cầu gửi danh sách có dấu phẩy (họ tên, mã OTP) không bị mất động từ, nhận diện đúng Rủi ro cao."""
    text = (
        "Công ty ABC tuyển Thực tập sinh kiểm thử. Lương: 4–6 triệu đồng/tháng. "
        "Email: hr@abc.example. Yêu cầu gửi họ tên, mã OTP ngân hàng qua Zalo."
    )
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"


def test_negated_unrealistic_income_not_flagged():
    """Mệnh đề phủ định lời hứa thu nhập (không cam kết kiếm 5 triệu...) không kích hoạt cảnh báo."""
    text = "Không cam kết kiếm 5 triệu đồng mỗi ngày chỉ với 10 phút, không cần kinh nghiệm."
    job, indicators, _, _, _, _, _ = perform_text_analysis(text)
    assert not any(ind.rule_id == "RULE_UNREALISTIC_INCOME" for ind in indicators)


def test_negated_cccd_with_otp_demand_triggers_risk():
    """Phủ định CCCD ở mệnh đề trước không triệt tiêu yêu cầu mã OTP ở mệnh đề có động từ mới."""
    text = "Không gửi CCCD nhưng yêu cầu gửi mã OTP ngân hàng qua Zalo."
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"


def test_negated_email_otp_with_zalo_otp_demand_triggers_risk():
    """Mệnh đề sau dấu phẩy có động từ mệnh lệnh (hãy gửi) phát hiện đúng yêu cầu OTP."""
    text = "Không gửi mã OTP qua email, hãy gửi mã OTP ngân hàng qua Zalo."
    job, indicators, risk_label_vi, _, _, _, _ = perform_text_analysis(text)
    assert any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)
    assert risk_label_vi == "Rủi ro cao"


def test_positive_cv_with_negated_otp_not_flagged():
    """Động từ gửi ở mệnh đề trước không nuốt mệnh đề phủ định OTP (không cung cấp) ở phía sau."""
    text = "Gửi CV, không cung cấp mã OTP ngân hàng."
    job, indicators, _, _, _, _, _ = perform_text_analysis(text)
    assert not any(ind.rule_id == "RULE_SENSITIVE_DATA" for ind in indicators)

