"""Regressions for R3 review: real trust boundaries, not runtime demo paths."""

import asyncio
import base64
import json
import socket
import time
import threading
from io import BytesIO
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from app.api.routes import extraction
from app.core.rate_limit import reset_rate_limits
from app.core.url_safety import URLSafetyError, validate_url_safety
from app.main import app
from app.services.ocr import OCRResult, extract_text_from_image
from app.services.url_extraction import VisibleTextHTMLParser, extract_text_from_url


@pytest.fixture
def client():
    reset_rate_limits()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    reset_rate_limits()


def test_image_upload_cors_preflight(client):
    response = client.options('/api/v1/extractions/image', headers={
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type,x-filename',
    })
    assert response.status_code == 200


@pytest.mark.parametrize('path,payload', [
    ('/image', []),
    ('/image', {'image_base64': 'AAAA', 'filename': 123}),
    ('/image', {'image_base64': 'AAAA', 'content_type': 123}),
    ('', ['url']),
    ('', {'url': 'https://example.com:notaport/job'}),
    ('/url', {'url': 'https://example.com:99999/job'}),
    ('/url', {'url': 'https://\ud800.com/job'}),
    ('/image', {'image_base64': 'AAAA', 'filename': '\ud800.png'}),
])
def test_invalid_extraction_payload_is_private_validation_error(client, path, payload):
    response = client.post('/api/v1/extractions' + path,
                           content=json.dumps(payload).encode('ascii'),
                           headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.headers['Cache-Control'] == 'no-store'


@pytest.mark.parametrize('url', ['https://example.com:no/job', 'https://example.com:99999/job'])
def test_malformed_ports_are_url_safety_errors(url):
    with pytest.raises(URLSafetyError):
        validate_url_safety(url)


def test_deeply_nested_json_is_a_private_validation_error(client):
    response = client.post('/api/v1/extractions/url',
                           content=b'{"url":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}',
                           headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.headers['Cache-Control'] == 'no-store'


@pytest.mark.parametrize('ip', ['100.64.0.1', '100.100.100.200'])
def test_shared_address_space_is_not_public(ip):
    with pytest.raises(URLSafetyError):
        validate_url_safety(f'http://{ip}/job')


def test_meta_tag_does_not_hide_the_body():
    parser = VisibleTextHTMLParser()
    parser.feed('<html><head><meta charset="utf-8"><title>Jobs</title></head>'
                '<body><h1>Hiring Backend engineers in Hanoi</h1></body></html>')
    assert parser.get_text() == 'Hiring Backend engineers in Hanoi'


def test_optional_head_end_tag_does_not_hide_the_body():
    parser = VisibleTextHTMLParser()
    parser.feed('<html><head><title>Jobs</title><body><h1>Hiring Backend engineers in Hanoi</h1></body></html>')
    assert parser.get_text() == 'Hiring Backend engineers in Hanoi'


def test_network_connection_uses_validated_ip_despite_dns_rebinding():
    attempts, lookups = [], []

    def resolve(host, port, *args, **kwargs):
        if host == '93.184.216.34':
            ip = host
        else:
            lookups.append(host)
            ip = '93.184.216.34' if len(lookups) == 1 else '127.0.0.1'
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]

    def connect(sock, address):
        attempts.append(address)
        raise OSError('Test prevents an actual connection')

    with httpx.Client(trust_env=False) as http_client:
        with patch('socket.getaddrinfo', side_effect=resolve), patch('socket.socket.connect', new=connect):
            extract_text_from_url('http://jobs.attacker.com/job', client=http_client)
    assert attempts == [('93.184.216.34', 80)]
    assert lookups == ['jobs.attacker.com']


def test_pinned_https_preserves_host_and_tls_server_name(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)),
    ])

    def respond(request):
        assert request.url.host == '93.184.216.34'
        assert request.headers['host'] == 'jobs.company.com'
        assert request.extensions['sni_hostname'] == 'jobs.company.com'
        return httpx.Response(200, text='Hiring Backend engineers in Hanoi', headers={'Content-Type': 'text/plain'})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http_client:
        result = extract_text_from_url('https://jobs.company.com/job', client=http_client)
    assert result.success


def test_url_stops_reading_at_download_limit():
    class Stream(httpx.SyncByteStream):
        read_bytes = 0

        def __iter__(self):
            for _ in range(48):
                self.read_bytes += 65536
                yield b'x' * 65536

    stream = Stream()
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, headers={'Content-Type': 'text/plain'}, stream=stream,
    ))) as http_client:
        result = extract_text_from_url('https://8.8.8.8/job', client=http_client)
    assert not result.success
    assert result.text is None
    assert stream.read_bytes <= 1024 * 1024 + 65536


def test_url_deadline_is_checked_for_each_small_chunk(monkeypatch):
    elapsed = [0]

    class SlowStream(httpx.SyncByteStream):
        reads = 0

        def __iter__(self):
            for _ in range(100):
                self.reads += 1
                elapsed[0] += 4
                yield b'x'

    monkeypatch.setattr('app.services.url_extraction.time.monotonic', lambda: elapsed[0])
    stream = SlowStream()
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, headers={'Content-Type': 'text/plain'}, stream=stream,
    ))) as http_client:
        result = extract_text_from_url('https://8.8.8.8/job', client=http_client)
    assert not result.success
    assert stream.reads == 2


def test_url_deadline_interrupts_slow_response_headers():
    import httpcore
    from httpcore._backends.sync import SyncStream

    client_socket, server_socket = socket.socketpair()
    wire = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 32\r\n\r\nHiring Backend engineers in Hanoi'

    def drip():
        try:
            for byte in wire:
                server_socket.sendall(bytes([byte]))
                time.sleep(.02)
        except OSError:
            pass
        finally:
            server_socket.close()

    class Backend(httpcore.NetworkBackend):
        def connect_tcp(self, *args, **kwargs):
            return SyncStream(client_socket)

    sender = threading.Thread(target=drip, daemon=True)
    sender.start()
    transport = httpx.HTTPTransport()
    transport._pool.close()
    transport._pool = httpcore.ConnectionPool(network_backend=Backend(), max_keepalive_connections=0)
    started = time.monotonic()
    try:
        with httpx.Client(transport=transport, trust_env=False) as http_client:
            result = extract_text_from_url('http://8.8.8.8/job', timeout=.1, client=http_client)
        assert not result.success
        assert time.monotonic() - started < .6
    finally:
        client_socket.close()
        sender.join(timeout=1)


def test_deadline_interrupts_tls_after_socket_wrapping():
    import httpcore
    from httpcore._backends.sync import SyncStream

    client_socket, server_socket = socket.socketpair()

    class Backend(httpcore.NetworkBackend):
        def connect_tcp(self, *args, **kwargs):
            time.sleep(.3)
            return SyncStream(client_socket)

    transport = httpx.HTTPTransport()
    transport._pool.close()
    transport._pool = httpcore.ConnectionPool(network_backend=Backend(), max_keepalive_connections=0)
    started = time.monotonic()
    try:
        with httpx.Client(transport=transport, trust_env=False) as http_client:
            result = extract_text_from_url('https://8.8.8.8/job', timeout=.5, client=http_client)
        assert not result.success
        assert time.monotonic() - started < .7
    finally:
        client_socket.close()
        server_socket.close()


def test_hidden_png_metadata_is_not_ocr_text():
    from PIL import Image, PngImagePlugin

    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('Description', 'Secret job text absent from the pixels')
    Image.new('RGB', (32, 32), 'white').save(output, format='PNG', pnginfo=metadata)
    with patch('app.services.ocr.run_system_tesseract', return_value=None):
        result = extract_text_from_image(output.getvalue())
    assert not result.success
    assert result.text is None


def test_demo_shaped_url_uses_actual_response():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404))) as http_client:
        result = extract_text_from_url('https://8.8.8.8/not-a-job.example/complete', client=http_client)
    assert not result.success
    assert result.text is None


def test_hidden_marker_is_not_ocr_text():
    fake_image = b'\x89PNG\r\n\x1a\nJOB_TEXT:Hidden text that is not image pixels'
    with patch('app.services.ocr.run_system_tesseract', return_value=None):
        result = extract_text_from_image(fake_image)
    assert not result.success
    assert result.text is None


def test_chunked_upload_stops_before_reading_the_whole_body():
    async def run():
        chunks = 0

        async def receive():
            nonlocal chunks
            chunks += 1
            return {'type': 'http.request', 'body': b'x' * (1024 * 1024), 'more_body': chunks < 12}

        scope = {'type': 'http', 'method': 'POST', 'path': '/api/v1/extractions/image',
                 'headers': [(b'content-type', b'image/png')], 'client': ('stream-test', 1), 'state': {}}
        reset_rate_limits()
        try:
            await extraction.extract_from_image_endpoint(Request(scope, receive), Response(), content_type='image/png')
        except Exception as exc:
            assert getattr(exc, 'status_code', None) == 413
        assert chunks <= 6

    asyncio.run(run())


def test_slow_ocr_does_not_block_the_event_loop():
    async def run():
        scope = {'type': 'http', 'method': 'POST', 'path': '/api/v1/extractions/image',
                 'headers': [(b'content-type', b'image/png')], 'client': ('async-test', 1), 'state': {}}

        async def receive():
            return {'type': 'http.request', 'body': b'fake-image', 'more_body': False}

        finished = asyncio.Event()

        async def tick():
            await asyncio.sleep(.01)
            finished.set()

        def ocr(*args, **kwargs):
            time.sleep(.15)
            assert finished.is_set(), 'OCR blocked the event loop'
            return OCRResult(success=False)

        reset_rate_limits()
        ticker = asyncio.create_task(tick())
        await asyncio.sleep(0)
        with patch.object(extraction, 'extract_text_from_image', side_effect=ocr):
            await extraction.extract_from_image_endpoint(Request(scope, receive), Response(), content_type='image/png')
        await ticker

    asyncio.run(run())
