"""HTTP contract and privacy over an isolated curated store."""

import logging
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.main import app
from app.core.rate_limit import reset_rate_limits
from app.db.session import get_db
from app.models.verifications import EmployerClaim
from app.models.guest_sessions import GuestSession
from app.models.analyses import Analysis
from tests.test_verification_store import verification_db, add_employer


@pytest.fixture
def client(verification_db):
    app.dependency_overrides[get_db] = lambda: verification_db
    reset_rate_limits()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()
    reset_rate_limits()


def test_stateless_verification_has_trace_and_provenance(client, verification_db):
    _, source = add_employer(verification_db)
    response = client.post("/api/v1/verifications", json={"tax_id": "0000000001"})
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Commit-SHA"]
    assert data["verification_label_vi"] == "Khớp nguồn đã xác minh"
    assert data["matched_sources"][0]["source_revision"] == 1
    assert "guest_session_token" not in data and "id" not in data
    assert verification_db.scalar(select(func.count()).select_from(GuestSession)) == 0
    assert verification_db.scalar(select(func.count()).select_from(Analysis)) == 0


@pytest.mark.parametrize("payload,code", [({}, "NO_INPUT_PROVIDED"), ({"tax_id": "01234567890"}, "VALIDATION_ERROR"), ({"company_name": "Mẫu", "is_demo": True}, "VALIDATION_ERROR")])
def test_structured_validation_error(client, payload, code):
    response = client.post("/api/v1/verifications", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"


def test_sensitive_invalid_input_is_not_echoed_in_error_or_logs(client, caplog):
    secret = "SECRET_BANK_NUMBER_12345678"
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = client.post("/api/v1/verifications", json={"bank_account": {"account_number": secret}, secret: "private"})
    assert response.status_code == 422
    assert secret not in response.text
    assert secret not in caplog.text


def test_malformed_json_is_sanitized(client):
    response = client.post("/api/v1/verifications", content='{"tax_id":"PRIVATE_VALUE"', headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert "PRIVATE_VALUE" not in response.text


@pytest.mark.parametrize("size_header", [False, True])
def test_oversized_body_rejected_before_json_parsing(client, size_header):
    headers = {"Content-Type": "application/json"}
    response = client.post("/api/v1/verifications", content=b"x" * 32769 if size_header else iter([b"x" * 20000, b"x" * 12769]), headers=headers)
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "PAYLOAD_TOO_LARGE"


def test_non_json_content_type_rejected(client):
    response = client.post("/api/v1/verifications", content="tax_id=0000000001", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415


def test_limit_is_separate_from_analysis(client):
    for _ in range(10):
        assert client.post("/api/v1/verifications", json={"company_name": "Mẫu"}).status_code == 200
    limited = client.post("/api/v1/verifications", json={"company_name": "Mẫu"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    assert limited.json()["detail"]["code"] == "RATE_LIMITED"
    assert client.post("/api/v1/analyses", json={"text": "Công ty Mẫu tuyển Tester."}).status_code == 201


def test_store_failure_is_not_unverified_success(client, monkeypatch):
    from app.api.routes import verifications
    def fail(*args, **kwargs):
        raise OperationalError("private", {}, Exception("PRIVATE_DATABASE_DETAIL"))
    monkeypatch.setattr(verifications, "load_employers", fail)
    response = client.post("/api/v1/verifications", json={"tax_id": "0000000001"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SOURCE_STORE_UNAVAILABLE"
    assert "PRIVATE_DATABASE_DETAIL" not in response.text


def test_unexpected_failure_is_sanitized(client, monkeypatch):
    from app.api.routes import verifications
    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE_RUNTIME_DETAIL")
    monkeypatch.setattr(verifications, "verify_claims", fail)
    response = client.post("/api/v1/verifications", json={"tax_id": "0000000001"})
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "INTERNAL_ERROR"
    assert "PRIVATE_RUNTIME_DETAIL" not in response.text


def test_analysis_uses_curated_sources_and_saved_snapshot_survives_revocation(client, verification_db):
    company, source = add_employer(verification_db)
    text = "Công ty Mẫu tuyển Tester. Lương: 8 triệu đồng/tháng. Email: HR@mau.example."
    created = client.post("/api/v1/analyses", json={"text": text})
    assert created.status_code == 201
    snapshot = created.json()
    assert snapshot["verification_label_vi"] == "Khớp nguồn đã xác minh"
    assert snapshot["evidence"]["matched_sources"][0]["source_revision"] == 1
    source.is_active = False
    source.source_revision = 2
    verification_db.commit()
    loaded = client.get(f"/api/v1/analyses/{snapshot['id']}", headers={"X-Guest-Session-Token": snapshot["guest_session_token"]})
    assert loaded.json()["evidence"] == snapshot["evidence"]
    newer = client.post("/api/v1/analyses", json={"text": text})
    assert newer.json()["verification_label_vi"] == "Chưa xác minh"


def test_matching_source_never_erases_deposit_warning(client, verification_db):
    add_employer(verification_db)
    text = "Công ty Mẫu tuyển Tester. Lương: 8 triệu đồng/tháng. Email: HR@mau.example. Đặt cọc 1.000.000 đồng trước phỏng vấn."
    result = client.post("/api/v1/analyses", json={"text": text}).json()
    assert result["verification_label_vi"] == "Khớp nguồn đã xác minh"
    assert result["risk_label_vi"] == "Rủi ro cao"


def test_api_error_has_cors_headers_for_allowed_frontend(client, monkeypatch):
    from app.api.routes import verifications
    def fail(*args, **kwargs):
        raise RuntimeError("unavailable")
    monkeypatch.setattr(verifications, "verify_claims", fail)
    response = client.post("/api/v1/verifications", json={"company_name": "Mẫu"}, headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 500
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
