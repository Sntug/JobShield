"""Unit tests for URL safety and SSRF protection (R3.2)."""

import pytest

from app.core.url_safety import (
    URLSafetyError,
    is_ip_private_or_restricted,
    validate_url_safety,
)


def test_empty_url_rejected():
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("")
    assert exc.value.code == "EMPTY_URL"


def test_oversized_url_rejected():
    long_url = "https://example.com/" + "a" * 2050
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety(long_url)
    assert exc.value.code == "URL_TOO_LONG"


@pytest.mark.parametrize(
    "bad_scheme",
    [
        "ftp://example.com/job",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<h1>Hello</h1>",
        "gopher://example.com",
    ],
)
def test_unsupported_scheme_rejected(bad_scheme):
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety(bad_scheme)
    assert exc.value.code == "UNSUPPORTED_SCHEME"


def test_userinfo_rejected():
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("https://admin:secret@example.com/jobs")
    assert exc.value.code == "USERINFO_NOT_ALLOWED"


@pytest.mark.parametrize("bad_port", [22, 25, 8080, 8443, 5432, 6379, 27017])
def test_unsupported_port_rejected(bad_port):
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety(f"http://example.com:{bad_port}/jobs")
    assert exc.value.code == "UNSUPPORTED_PORT"


@pytest.mark.parametrize(
    "blocked_host",
    [
        "http://localhost/jobs",
        "https://localhost:443/jobs",
        "http://app.localhost/jobs",
        "http://metadata.google.internal/computeMetadata/v1",
        "http://service.local/jobs",
        "http://database.internal/jobs",
        "http://backend.lan/jobs",
    ],
)
def test_ssrf_blocked_hosts_rejected(blocked_host):
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety(blocked_host)
    assert exc.value.code in ("SSRF_BLOCKED_HOST", "SSRF_PRIVATE_IP")


@pytest.mark.parametrize(
    "private_ip_url",
    [
        "http://127.0.0.1/jobs",
        "http://127.0.0.2/jobs",
        "http://10.0.0.1/jobs",
        "http://10.255.255.255/jobs",
        "http://172.16.0.1/jobs",
        "http://172.31.255.255/jobs",
        "http://192.168.1.1/jobs",
        "http://192.168.0.100/jobs",
        "http://169.254.169.254/latest/meta-data",
        "http://0.0.0.0/jobs",
        "http://[::1]/jobs",
    ],
)
def test_ssrf_private_ips_rejected(private_ip_url):
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety(private_ip_url)
    assert exc.value.code == "SSRF_PRIVATE_IP"


def test_test_domains_do_not_bypass_dns_validation(monkeypatch):
    import socket

    def no_dns(*args, **kwargs):
        raise socket.gaierror("No DNS")

    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("https://tin-demo.example/dang-nhap")
    assert exc.value.code == "DNS_RESOLUTION_FAILED"


def test_resolved_private_ip_rejected(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.50", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(URLSafetyError) as exc:
        validate_url_safety("https://public-looking-domain.com/jobs")
    assert exc.value.code == "SSRF_RESOLVED_PRIVATE_IP"
