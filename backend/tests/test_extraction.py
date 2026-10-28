"""Integration and API tests for extraction endpoints (R3)."""

import base64
import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import reset_rate_limits
from app.main import app

from tests.extraction_helpers import JOB_TEXT, image_bytes

SAMPLE_PNG = image_bytes()


@pytest.fixture
def client(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
    ])

    def respond(self, request):
        if request.url.path == "/dang-nhap":
            return httpx.Response(401)
        return httpx.Response(200, headers={"Content-Type": "text/html"},
                              text=f'<html><head><meta charset="utf-8"></head><body><p>{JOB_TEXT}</p></body></html>')

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", respond)
    monkeypatch.setattr("app.services.ocr.run_system_tesseract", lambda _: JOB_TEXT)
    reset_rate_limits()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    reset_rate_limits()


def test_url_extraction_api_success(client):
    response = client.post(
        "/api/v1/extractions/url",
        json={"url": "https://tin-demo.example/complete"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["source_type"] == "url"
    assert "tuyendung@mau-a.example" in data["text"]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Commit-SHA"]


def test_url_extraction_api_blocked_scenario(client):
    response = client.post(
        "/api/v1/extractions/url",
        json={"url": "https://tin-demo.example/dang-nhap"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["text"] is None
    assert "yêu cầu đăng nhập" in data["failure_vi"]


def test_url_extraction_validation_errors(client):
    res_empty = client.post("/api/v1/extractions/url", json={"url": "   "})
    assert res_empty.status_code == 422

    res_missing = client.post("/api/v1/extractions/url", json={})
    assert res_missing.status_code == 422


def test_image_extraction_api_json_base64_success(client):
    b64 = base64.b64encode(SAMPLE_PNG).decode("ascii")
    response = client.post(
        "/api/v1/extractions/image",
        json={"image_base64": b64, "filename": "recruitment.png"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["source_type"] == "image"
    assert "Cong ty Cong nghe ABC" in data["text"]
    assert response.headers["Cache-Control"] == "no-store"


def test_image_extraction_api_raw_binary_success(client):
    response = client.post(
        "/api/v1/extractions/image",
        content=SAMPLE_PNG,
        headers={"Content-Type": "image/png", "X-Filename": "sample.png"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Cong ty Cong nghe ABC" in data["text"]


def test_image_extraction_api_blurry_failure(client, monkeypatch):
    monkeypatch.setattr("app.services.ocr.run_system_tesseract", lambda _: None)
    blurry_bytes = SAMPLE_PNG
    b64 = base64.b64encode(blurry_bytes).decode("ascii")
    response = client.post(
        "/api/v1/extractions/image",
        json={"image_base64": b64},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["text"] is None
    assert "dán hoặc nhập" in data["failure_vi"]


def test_generic_extraction_endpoint(client):
    # Test URL dispatch
    res_url = client.post(
        "/api/v1/extractions",
        json={"url": "https://tin-demo.example/complete"},
    )
    assert res_url.status_code == 200
    assert res_url.json()["success"] is True
    assert res_url.json()["source_type"] == "url"

    # Test Image dispatch
    b64 = base64.b64encode(SAMPLE_PNG).decode("ascii")
    res_img = client.post(
        "/api/v1/extractions",
        json={"image_base64": b64},
    )
    assert res_img.status_code == 200
    assert res_img.json()["success"] is True
    assert res_img.json()["source_type"] == "image"


def test_extraction_rate_limiting(client):
    for _ in range(10):
        res = client.post(
            "/api/v1/extractions/url",
            json={"url": "https://tin-demo.example/complete"},
        )
        assert res.status_code == 200

    limited = client.post(
        "/api/v1/extractions/url",
        json={"url": "https://tin-demo.example/complete"},
    )
    assert limited.status_code == 429
    assert limited.headers.get("Retry-After")
