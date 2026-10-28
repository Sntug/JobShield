"""Extraction failures exercise real services with only external I/O replaced."""

import socket

import httpx
import pytest

from app.services.ocr import extract_text_from_image
from app.services.url_extraction import extract_text_from_url
from tests.extraction_helpers import image_bytes


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
    ])


def test_ocr_failure_blurry_image(monkeypatch):
    monkeypatch.setattr("app.services.ocr.run_system_tesseract", lambda _: None)
    result = extract_text_from_image(image_bytes())
    assert not result.success
    assert result.text is None
    assert "dán hoặc nhập" in result.failure_vi


def test_ocr_failure_unreadable_image():
    result = extract_text_from_image(b"\x89PNG\r\n\x1a\nnot-an-image")
    assert not result.success
    assert result.text is None
    assert result.failure_vi


@pytest.mark.parametrize("status", [401, 403])
def test_url_http_401_403_access_denied(status):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status))) as client:
        result = extract_text_from_url("https://tuyendung.example/private-job", client=client)
    assert not result.success
    assert result.text is None
    assert "yêu cầu đăng nhập" in result.failure_vi


def test_url_login_wall_in_html():
    html = "<html><body><h1>Vui lòng đăng nhập để xem tin tuyển dụng này</h1></body></html>"
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, text=html, headers={"Content-Type": "text/html"},
    ))) as client:
        result = extract_text_from_url("https://tuyendung.example/job", client=client)
    assert not result.success
    assert result.text is None
    assert "yêu cầu đăng nhập" in result.failure_vi


def test_url_timeout_handled():
    def timeout(request):
        raise httpx.ReadTimeout("Test timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        result = extract_text_from_url("https://slow-recruitment.example/job", client=client)
    assert not result.success
    assert result.text is None
    assert "thời gian chờ" in result.failure_vi


def test_url_ssrf_rejected_cleanly():
    result = extract_text_from_url("http://127.0.0.1:8080/admin/jobs")
    assert not result.success
    assert result.text is None
    assert "cổng" in result.failure_vi.lower()


@pytest.mark.parametrize('format', ['PNG', 'JPEG', 'WEBP'])
def test_ocr_reads_real_pixels(format):
    import os
    import shutil
    import unicodedata
    from io import BytesIO
    from pathlib import Path
    from PIL import Image

    if not shutil.which('tesseract'):
        if os.getenv('OCR_REQUIRED') == '1':
            pytest.fail('Tesseract must be installed in the OCR verification environment')
        pytest.skip('Real OCR runs in Docker and CI with Tesseract vie+eng installed')
    output = BytesIO()
    with Image.open(Path(__file__).parent / 'fixtures/r3-job.png') as image:
        image.save(output, format=format)
    result = extract_text_from_image(output.getvalue())
    assert result.success, result.failure_vi
    normalized = ''.join(c for c in unicodedata.normalize('NFD', result.text.lower()) if not unicodedata.combining(c))
    assert 'backend' in normalized
    assert '20' in normalized
    assert 'khong thu phi' in normalized
