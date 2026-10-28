"""Privacy and security safeguards tests (R1-R3)."""

import pytest
from fastapi.testclient import TestClient

from app.core.privacy import (
    get_privacy_headers,
    sanitize_url_for_logging,
)
from app.core.rate_limit import reset_rate_limits
from app.main import app


@pytest.fixture
def client():
    reset_rate_limits()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    reset_rate_limits()


def test_sanitize_url_for_logging_removes_sensitive_params():
    url = "https://tuyendung.example/job?token=SUPER_SECRET_123&utm_source=fb&apiKey=XYZ999&auth=ABC"
    cleaned = sanitize_url_for_logging(url)
    assert "SUPER_SECRET_123" not in cleaned
    assert "XYZ999" not in cleaned
    assert "ABC" not in cleaned
    assert "utm_source=fb" in cleaned
    assert "REDACTED" in cleaned


def test_sanitize_url_userinfo_removed():
    url = "https://user:password123@tuyendung.example/job"
    cleaned = sanitize_url_for_logging(url)
    assert "password123" not in cleaned
    assert "user@" not in cleaned


def test_privacy_headers():
    headers = get_privacy_headers()
    assert headers["Cache-Control"] == "no-store"
    assert headers["Pragma"] == "no-cache"


@pytest.mark.parametrize(
    "path,method,payload",
    [
        ("/api/v1/extractions/url", "POST", {"url": "https://tin-demo.example/complete"}),
        ("/api/v1/extractions", "POST", {"url": "https://tin-demo.example/complete"}),
    ],
)
def test_all_sensitive_endpoints_have_no_store(client, path, method, payload):
    if method == "POST":
        res = client.post(path, json=payload)
    else:
        res = client.get(path)
    assert res.headers.get("Cache-Control") == "no-store"
