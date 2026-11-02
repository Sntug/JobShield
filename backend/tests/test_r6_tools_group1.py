"""Focused regressions for the R6 release and load-test tools."""

import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_script("post_release_smoke", "scripts/post-release-smoke.py")
load_test = load_script("load_test", "scripts/load-test.py")


class FakeHTTPResponse:
    status = 200
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit):
        return b"{}"


@pytest.mark.parametrize(
    ("target", "should_send_secret"),
    [
        ("https://job-shield-r6-review-sntug.vercel.app", True),
        ("http://job-shield-r6-review-sntug.vercel.app", False),
        ("https://job-shield-r6-review-sntug.vercel.app.evil.example", False),
        ("https://evil.example/job-shield-r6-review-sntug.vercel.app", False),
        ("https://job-shield-r6-review-sntug.vercel.app/path", False),
        ("https://job-shield-r6-review-sntug.vercel.app?next=/", False),
    ],
)
def test_smoke_sends_bypass_secret_only_to_https_jobshield_preview(monkeypatch, target, should_send_secret):
    monkeypatch.setenv("VERCEL_AUTOMATION_BYPASS_SECRET", "synthetic-test-secret")
    requests = []

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            return FakeHTTPResponse()

    monkeypatch.setattr(smoke, "build_opener", lambda *_: Opener())

    smoke.request_api(target, "/healthz")

    sent_secret = requests[0].get_header("X-vercel-protection-bypass")
    assert (sent_secret == "synthetic-test-secret") is should_send_secret


def run_restore_drill(tmp_path, *, fail_restore=False):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    mode_log = tmp_path / "created-mode.txt"
    docker = bin_dir / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        "case \" $* \" in\n"
        "  *' pg_dump '*)\n"
        "    artifact=$(find \"$TMPDIR\" -maxdepth 1 -name 'jobshield_drill.*' -print -quit)\n"
        "    test -n \"$artifact\" || exit 31\n"
        "    mode=$(stat -c '%a' \"$artifact\" 2>/dev/null || stat -f '%Lp' \"$artifact\")\n"
        "    printf '%s' \"$mode\" > \"$MODE_LOG\"\n"
        "    printf 'synthetic archive'\n"
        "    ;;\n"
        "  *' pg_restore '*)\n"
        "    cat >/dev/null\n"
        "    test \"${FAIL_RESTORE:-0}\" != 1 || exit 9\n"
        "    ;;\n"
        "  *' psql '*) printf '0\\n' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    env = {
        **os.environ,
        "TMPDIR": str(tmp_path),
        "MODE_LOG": str(mode_log),
        "FAIL_RESTORE": "1" if fail_restore else "0",
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "DB_PASSWORD": "synthetic-test-password",
    }
    result = subprocess.run(
        ["bash", "-c", 'umask 022; exec "$@"', "restore-test", str(REPO_ROOT / "scripts/restore-drill.sh")],
        cwd=REPO_ROOT,
        env=env,
        input="",
        capture_output=True,
        text=True,
        check=False,
    )
    return result, mode_log


def test_restore_drill_creates_private_backup_under_umask_022_and_cleans_it(tmp_path):
    result, mode_log = run_restore_drill(tmp_path)

    assert result.returncode == 0, result.stderr + result.stdout
    assert mode_log.read_text(encoding="utf-8").strip() == "600"
    assert not list(tmp_path.glob("jobshield_drill.*"))


def test_restore_drill_cleans_private_backup_after_restore_failure(tmp_path):
    result, _ = run_restore_drill(tmp_path, fail_restore=True)

    assert result.returncode != 0
    assert not list(tmp_path.glob("jobshield_drill.*"))


class FakeRateResponse:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self.headers = headers or {}

    def json(self):
        return {}


def test_rate_limit_probe_retries_dirty_window_then_requires_ten_and_429(monkeypatch):
    requests = []
    statuses = [(429, {"Retry-After": "5"})] + [(201, {})] * 10 + [(429, {"Retry-After": "60"})]

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def request(self, method, url, *, json, headers):
            requests.append((method, url, headers))
            status, response_headers = statuses.pop(0)
            return FakeRateResponse(status, response_headers)

    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(load_test.httpx, "AsyncClient", lambda **_: FakeAsyncClient())
    monkeypatch.setattr(load_test.asyncio, "sleep", fake_sleep)

    result = asyncio.run(load_test.test_rate_limiting("https://preview.example"))

    assert result["rate_limited_properly"] is True
    assert result["status_sequence"] == [201] * 10 + [429]
    assert result["retry_after_seconds"] == 60
    assert 60 <= result["retry_after_window_seconds"] <= 63
    assert waits == [61]
    assert len(requests) == 12
    assert all(headers in (None, {}) for _, _, headers in requests)


def test_rate_limit_probe_fails_on_error_early_or_late_limiter(monkeypatch):
    async def run_with(statuses):
        async def no_sleep(_seconds):
            return None

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return False

            async def request(self, *_args, **_kwargs):
                status, headers = statuses.pop(0)
                return FakeRateResponse(status, headers)

        monkeypatch.setattr(load_test.httpx, "AsyncClient", lambda **_: FakeAsyncClient())
        monkeypatch.setattr(load_test.asyncio, "sleep", no_sleep)
        return await load_test.test_rate_limiting("https://preview.example")

    early = asyncio.run(run_with([(429, {"Retry-After": "2"})] * 12))
    error = asyncio.run(run_with([(500, {})] + [(201, {})] * 10))
    late = asyncio.run(run_with([(201, {})] * 11))
    missing_retry_after = asyncio.run(run_with([(201, {})] * 10 + [(429, {})]))
    short_window = asyncio.run(run_with([(201, {})] * 10 + [(429, {"Retry-After": "1"})]))
    long_window = asyncio.run(run_with([(201, {})] * 10 + [(429, {"Retry-After": "120"})]))

    assert early["rate_limited_properly"] is False
    assert error["rate_limited_properly"] is False
    assert late["rate_limited_properly"] is False
    assert missing_retry_after["rate_limited_properly"] is False
    assert short_window["rate_limited_properly"] is False
    assert long_window["rate_limited_properly"] is False


def test_retry_after_validation_accounts_for_elapsed_probe_time():
    assert load_test.retry_after_matches_window(57, 3.0) is True
    assert load_test.retry_after_matches_window(1, 0.0) is False
    assert load_test.retry_after_matches_window(120, 0.0) is False


def test_rate_window_reset_waits_for_the_full_window_without_client_headers(monkeypatch):
    requests = []
    statuses = [(201, {})] * 10 + [(429, {"Retry-After": "51"})]

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def request(self, method, url, *, json, headers):
            requests.append((method, url, headers))
            status, response_headers = statuses.pop(0)
            return FakeRateResponse(status, response_headers)

    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(load_test.httpx, "AsyncClient", lambda **_: FakeAsyncClient())
    monkeypatch.setattr(load_test.asyncio, "sleep", fake_sleep)

    result = asyncio.run(load_test.clear_rate_limit_window("https://preview.example"))

    assert result["clean"] is True
    assert result["wait_seconds"] == 61
    assert waits == [61]
    assert all(headers in (None, {}) for _, _, headers in requests)


def test_empty_or_failed_benchmark_samples_do_not_meet_p95(monkeypatch):
    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

    monkeypatch.setattr(load_test.httpx, "AsyncClient", lambda **_: FakeAsyncClient())

    async def fail_request(*_args, **_kwargs):
        return {"elapsed_seconds": 0.01, "success": False, "status_code": 0}

    monkeypatch.setattr(load_test, "execute_request", fail_request)
    empty = asyncio.run(load_test.run_analysis_benchmark("https://preview.example", 1, 0, 100))
    failed = asyncio.run(load_test.run_analysis_benchmark("https://preview.example", 1, 1, 100))
    empty_verification = asyncio.run(load_test.run_verification_benchmark("https://preview.example", 1, 0))
    failed_verification = asyncio.run(load_test.run_verification_benchmark("https://preview.example", 1, 1))

    outcomes = iter([
        {"elapsed_seconds": 0.01, "success": True, "status_code": 201},
        {"elapsed_seconds": 0.02, "success": False, "status_code": 0},
    ])

    async def mixed_request(*_args, **_kwargs):
        return next(outcomes)

    monkeypatch.setattr(load_test, "execute_request", mixed_request)
    mixed = asyncio.run(load_test.run_analysis_benchmark("https://preview.example", 1, 2, 100))
    outcomes = iter([
        {"elapsed_seconds": 0.01, "success": True, "status_code": 201},
        {"elapsed_seconds": 0.02, "success": False, "status_code": 0},
    ])
    mixed_verification = asyncio.run(load_test.run_verification_benchmark("https://preview.example", 1, 2))

    assert empty["meets_target_p95"] is False
    assert failed["meets_target_p95"] is False
    assert mixed["meets_target_p95"] is False
    assert empty_verification["meets_target_p95"] is False
    assert failed_verification["meets_target_p95"] is False
    assert mixed_verification["meets_target_p95"] is False


def test_acceptance_checks_use_every_reported_threshold():
    analysis = {
        "total_requests": 10,
        "sample_count": 10,
        "success_count": 10,
        "error_count": 0,
        "error_rate_pct": 0,
        "throughput_rps": 6,
        "latency_p50_s": 0.9,
        "latency_p90_s": 1.9,
        "latency_p95_s": 2.9,
        "latency_max_s": 4.9,
        "meets_target_p95": True,
    }
    verification = {
        "total_requests": 10,
        "sample_count": 10,
        "success_count": 10,
        "error_count": 0,
        "error_rate_pct": 0,
        "throughput_rps": 11,
        "latency_p50_s": 0.19,
        "latency_p95_s": 0.9,
        "meets_target_p95": True,
    }

    checks = load_test.evaluate_acceptance_checks(analysis, verification, True, True)
    assert all(checks.values())

    for field, value, check_name in [
        ("error_rate_pct", 0.01, "analysis_error_rate"),
        ("throughput_rps", 5, "analysis_throughput"),
        ("latency_p50_s", 1.0, "analysis_p50"),
        ("latency_p90_s", 2.0, "analysis_p90"),
        ("latency_p95_s", 3.0, "analysis_p95"),
        ("latency_max_s", 5.0, "analysis_max"),
    ]:
        candidate = analysis.copy()
        candidate[field] = value
        assert load_test.evaluate_acceptance_checks(candidate, verification, True, True)[check_name] is False

    for field, value, check_name in [
        ("error_rate_pct", 0.01, "verification_error_rate"),
        ("throughput_rps", 10, "verification_throughput"),
        ("latency_p50_s", 0.2, "verification_p50"),
        ("latency_p95_s", 1.0, "verification_p95"),
    ]:
        candidate = verification.copy()
        candidate[field] = value
        assert load_test.evaluate_acceptance_checks(analysis, candidate, True, True)[check_name] is False

    candidate = verification.copy()
    candidate["meets_target_p95"] = False
    assert load_test.evaluate_acceptance_checks(analysis, candidate, True, True)["verification_p95"] is False

    checks = load_test.evaluate_acceptance_checks(analysis, verification, False, True)
    assert checks["payload_limit"] is False


def test_load_tool_exits_nonzero_when_target_is_unready(monkeypatch):
    class UnreadyResponse:
        status_code = 503

    readiness_urls = []

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url, **_kwargs):
            readiness_urls.append(url)
            return UnreadyResponse()

    monkeypatch.setattr(load_test.httpx, "AsyncClient", lambda **_: FakeAsyncClient())
    monkeypatch.setattr(sys, "argv", ["load-test.py", "--target", "https://preview.example"])

    assert asyncio.run(load_test.main()) == 1
    assert readiness_urls == ["https://preview.example/ready"]


def test_load_tool_exits_nonzero_when_any_acceptance_check_fails(monkeypatch, tmp_path):
    class ReadyResponse:
        status_code = 200

        def json(self):
            return {"status": "ready", "database": "connected", "schema": "current"}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, *_args, **_kwargs):
            return ReadyResponse()

    async def analysis(*_args):
        return {
            "total_requests": 1, "sample_count": 1, "success_count": 1, "error_count": 0,
            "error_rate_pct": 0,
            "throughput_rps": 6, "latency_p50_s": 0.5, "latency_p90_s": 1,
            "latency_p95_s": 2, "latency_max_s": 3, "meets_target_p95": True,
            "text_length_chars": 100,
        }

    async def verification(*_args):
        return {
            "total_requests": 1, "sample_count": 1, "success_count": 1, "error_count": 0,
            "error_rate_pct": 0,
            "throughput_rps": 11, "latency_p50_s": 0.1,
            "latency_p95_s": 0.5, "meets_target_p95": True,
        }

    async def passed(*_args):
        return {"status_code": 422, "rejected_properly": True}

    async def failed(*_args):
        return {
            "rate_limited_properly": False,
            "total_probed": 11,
            "clean_window_wait_seconds": 0,
            "status_sequence": [201] * 11,
            "retry_after_seconds": None,
        }

    async def clean_window(*_args):
        return {"clean": True, "total_probed": 11, "wait_seconds": 0}

    monkeypatch.setattr(load_test.httpx, "AsyncClient", lambda **_: FakeAsyncClient())
    monkeypatch.setattr(load_test, "run_analysis_benchmark", analysis)
    monkeypatch.setattr(load_test, "run_verification_benchmark", verification)
    monkeypatch.setattr(load_test, "test_payload_limits", passed)
    monkeypatch.setattr(load_test, "test_rate_limiting", failed)
    monkeypatch.setattr(load_test, "clear_rate_limit_window", clean_window)
    report_path = tmp_path / "load-report.md"
    monkeypatch.setattr(sys, "argv", ["load-test.py", "--output", str(report_path)])

    assert asyncio.run(load_test.main()) == 1
    report = report_path.read_text(encoding="utf-8")
    assert "**Kết quả acceptance:** **FAIL**" in report
    assert "| **Độ trễ p95** | **2 giây** | **< 3.0 giây** | **PASS** |" in report
    assert "Retry-After `missing` (`FAIL`)" in report
