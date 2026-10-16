"""Kiểm tra các endpoints cơ bản của main.py trong R0.2."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint_returns_ok() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "JobShield API" in data["message"]


def test_healthz_endpoint_returns_healthy() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ready_endpoint_without_db_returns_503(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    response = client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["database"] == "unconfigured"


def test_request_tracing_middleware_generates_id_and_commit() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0
    assert "X-Commit-SHA" in response.headers


def test_request_tracing_ignores_incoming_client_id_and_logs(caplog) -> None:
    import logging

    custom_id = "test-request-id-12345"
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = client.get("/healthz", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    returned_id = response.headers["X-Request-ID"]
    assert returned_id != custom_id
    assert len(returned_id) == 32
    assert f"request_id={returned_id}" in caplog.text
    assert "status=200" in caplog.text
