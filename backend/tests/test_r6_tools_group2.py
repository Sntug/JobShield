"""Focused checks for R6 release-tool SHA and PostgreSQL archive behavior."""

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SMOKE_PATH = ROOT / "scripts" / "post-release-smoke.py"
SPEC = importlib.util.spec_from_file_location("post_release_smoke", SMOKE_PATH)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def test_smoke_sha_requires_a_present_nonempty_matching_header(monkeypatch):
    expected_sha = "abcdef0123456789"

    def run_with_sha(sha_header, expected):
        def request_api(_target, path, method="GET", payload=None, headers=None, **_kwargs):
            if path == "/healthz":
                response_headers = {"x-request-id": "request-1"}
                if sha_header is not None:
                    response_headers["x-commit-sha"] = sha_header
                return 200, {}, response_headers, 0.001
            if path == "/ready":
                return 200, {"status": "ready", "database": "connected", "schema": "current"}, {}, 0.001
            if path == "/api/v1/analyses" and method == "POST":
                if len(payload["text"]) > 10000:
                    return 422, {}, {}, 0.001
                return 201, {"id": "analysis-1", "guest_session_token": "synthetic-token", "risk_label_vi": "Rủi ro cao"}, {}, 0.001
            if path == "/api/v1/analyses/analysis-1":
                return (200 if headers else 404), {"id": "analysis-1"}, {}, 0.001
            if path == "/api/v1/verifications":
                return 200, {"verification_label_vi": "Chưa xác minh"}, {}, 0.001
            if path == "/api/v1/warnings":
                return 200, {"items": []}, {}, 0.001
            if path == "/api/v1/admin/reports":
                return 401, {}, {}, 0.001
            if path == "/api/v1/auth/login":
                return 401, {}, {"cache-control": "no-store"}, 0.001
            raise AssertionError(f"Unexpected smoke request: {method} {path}")

        monkeypatch.setattr(smoke, "request_api", request_api)
        return smoke.run_post_release_checks("http://example.test", expected)

    for sha_header in (None, "", "wrong00"):
        result = run_with_sha(sha_header, expected_sha)
        assert result["checks"][0]["passed"] is False
        assert result["all_passed"] is False

    result = run_with_sha(expected_sha[:7], expected_sha)
    assert result["checks"][0]["passed"] is True
    assert run_with_sha("", "")["checks"][0]["passed"] is False


@pytest.mark.parametrize("secret", ["line\nbreak", "non-ascii-é", "x" * 4097])
def test_smoke_rejects_malformed_bypass_secret_without_sending_it(monkeypatch, secret):
    monkeypatch.setenv("VERCEL_AUTOMATION_BYPASS_SECRET", secret)
    monkeypatch.setattr(smoke, "build_opener", lambda *_: pytest.fail("Invalid secret must not reach the HTTP client."))

    status, body, headers, _ = smoke.request_api(
        "https://job-shield-r6-review-sntug.vercel.app", "/healthz"
    )

    assert status == 0
    assert body == {"error": "Invalid VERCEL_AUTOMATION_BYPASS_SECRET format."}
    assert headers == {}


def test_smoke_report_for_failed_sha_does_not_claim_readiness_or_no_pii(tmp_path, monkeypatch):
    expected_sha = "abcdef0123456789"
    checks = [{
        "name": "1. Health Endpoint & Trace Headers (/healthz)",
        "passed": False,
        "latency_s": 0.001,
        "details": "HTTP 200, Commit: N/A, Request-ID: request-1",
    }] + [
        {"name": f"check-{index}", "passed": True, "latency_s": 0.001, "details": "ok"}
        for index in range(2, 9)
    ]
    results = {
        "timestamp": "2026-11-02 12:00:00",
        "target_url": "https://job-shield-r6-review-sntug.vercel.app",
        "expected_sha": expected_sha,
        "all_passed": False,
        "passed_checks": 7,
        "total_checks": 8,
        "checks": checks,
    }
    report_path = tmp_path / "smoke.md"
    monkeypatch.setattr(smoke, "run_post_release_checks", lambda _url, _sha: results)
    monkeypatch.setattr(sys, "argv", ["post-release-smoke.py", "--url", results["target_url"], "--sha", expected_sha, "--output", str(report_path)])

    with pytest.raises(SystemExit) as exit_result:
        smoke.main()

    report = report_path.read_text(encoding="utf-8")
    assert exit_result.value.code == 1
    assert "KHÔNG ĐẠT (FAIL)" in report
    assert "Commit: N/A" in report
    assert "Một hoặc nhiều kiểm tra thất bại" in report
    assert "Toàn bộ các endpoint nghiệp vụ" not in report
    assert "Không phát sinh rò rỉ dữ liệu cá nhân" not in report
    assert "Sẵn sàng bàn giao" not in report
