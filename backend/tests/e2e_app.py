"""Loopback-only API entry point for browser acceptance tests.

URL fetching still runs through the production SSRF checks and HTML parser. Only
the outbound HTTP transport is replaced so the test never reaches the network.
"""

import os
import ipaddress
from threading import Event

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import make_url


def _require_isolated_e2e_database() -> None:
    raw_url = os.environ.get("DATABASE_URL")
    if os.environ.get("JOBSHIELD_E2E_URL_FIXTURE") != "1" or not raw_url:
        raise RuntimeError("E2E URL fixture requires an explicit DATABASE_URL and JOBSHIELD_E2E_URL_FIXTURE=1")

    target = make_url(raw_url)
    if target.host not in {"127.0.0.1", "localhost"} or not (target.database or "").startswith(
        ("jobshield_r12_e2e_", "jobshield_ci_e2e")
    ):
        raise RuntimeError("Refusing E2E URL fixture outside a named loopback E2E database")


_require_isolated_e2e_database()

from app.main import app  # noqa: E402
from app.services import batch_analysis, url_extraction  # noqa: E402

_url_started = Event()
_url_released = Event()
# The loopback proxy maps per-test identities into TEST-NET-2 before forwarding.
_test_proxy_clients = ipaddress.ip_network("2001:db8::/32")
_mock_http = httpx.Client(transport=httpx.MockTransport(lambda request: _mock_url_response(request)))
_extract_text_from_url = url_extraction.extract_text_from_url


def _mock_url_response(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/jobshield-e2e-success":
        _url_started.set()
        if not _url_released.wait(timeout=20):
            return httpx.Response(504, text="E2E URL fixture release timed out")
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=(
                "<html><body><h1>Công ty E2E A tuyển kỹ sư QA</h1>"
                "<p>Lương 15 triệu đồng mỗi tháng. Không thu phí đặt cọc."
                " Gửi hồ sơ qua email hr@e2e-a.example.</p></body></html>"
            ),
        )
    if request.url.path == "/jobshield-e2e-error":
        return httpx.Response(503, text="Synthetic upstream unavailable")
    return httpx.Response(404, text="Unknown E2E URL fixture")


def _extract_with_mock_transport(url: str, *args, **kwargs):
    kwargs["client"] = _mock_http
    return _extract_text_from_url(url, *args, **kwargs)


# The batch worker's normal service call goes through the real URL extraction
# function, with only its HTTP client replaced by the loopback test fixture.
batch_analysis.extract_text_from_url = _extract_with_mock_transport


@app.get("/api/v1/__e2e__/url-fixture")
def url_fixture_ready():
    return {"ready": True, "kind": "mock-transport"}


@app.middleware("http")
async def only_loopback(request: Request, call_next):
    peer = request.client.host if request.client else ""
    try:
        peer_ip = ipaddress.ip_address(peer)
        is_loopback = peer_ip.is_loopback or peer_ip in _test_proxy_clients
    except ValueError:
        is_loopback = False
    if not is_loopback:
        return JSONResponse({"detail": "E2E fixture is loopback-only"}, status_code=403)
    return await call_next(request)


@app.get("/api/v1/__e2e__/url-state")
def url_fixture_state():
    return {"started": _url_started.is_set(), "released": _url_released.is_set()}


@app.post("/api/v1/__e2e__/url-release")
def release_url_fixture():
    _url_released.set()
    return {"released": True}


@app.post("/api/v1/__e2e__/url-reset")
def reset_url_fixture():
    if _url_started.is_set() and not _url_released.is_set():
        raise HTTPException(status_code=409, detail="Cannot reset an active URL fixture")
    _url_started.clear()
    _url_released.clear()
    return {"reset": True}
