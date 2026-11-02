#!/usr/bin/env python3
"""JobShield Automated Performance & Load Testing Tool (R6.1).

Tiêu chí đánh giá theo Kế hoạch bàn giao JobShield (mục 6.2):
- Concurrency: 5-10 request text đồng thời.
- Kích thước văn bản: tối đa 10.000 ký tự.
- Ngưỡng hiệu năng: p95 dưới 3.0 giây cho rule-only trên service đã sẵn sàng.
- Kiểm tra rate limit (429) và payload limit (422/413 khi vượt 10.000 ký tự).
- Kiểm tra quota từ IP thật, không giả lập client header; dirty windows có thể cần tối đa hai lần chờ 61s.
- Báo cáo số liệu: latency p50, p90, p95, p99, error rate, throughput (RPS).
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import statistics
import time
from typing import Any, Dict, List, Optional
import httpx


REALISTIC_JOB_TEXT = (
    "Công ty Cổ phần Công nghệ ABC tuyển dụng Kỹ sư Phần mềm Full-Stack tại Hà Nội. "
    "Mô tả công việc: Thiết kế, xây dựng và vận hành hệ thống Web backend FastAPI và frontend Next.js. "
    "Yêu cầu: Thành thạo Python, TypeScript, PostgreSQL, Docker, Git. "
    "Mức lương: 25 - 35 triệu đồng/tháng. Đãi ngộ: Thưởng dự án, bảo hiểm sức khỏe toàn diện. "
    "Quy trình ứng tuyển: Ứng viên nộp CV qua email tuyendung@abc-tech.example, "
    "hoặc website chính thức https://abc-tech.example/careers. "
    "Tuyệt đối không thu bất kỳ khoản phí hồ sơ, phí đặt cọc hay yêu cầu nạp tiền nào từ ứng viên."
)

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_WINDOW_TOLERANCE_SECONDS = 2


def generate_text_payload(target_length: int) -> str:
    """Tạo văn bản tuyển dụng có độ dài xấp xỉ target_length (tối đa 10.000 ký tự)."""
    if target_length <= len(REALISTIC_JOB_TEXT):
        return REALISTIC_JOB_TEXT[:target_length]
    repeat_count = (target_length // len(REALISTIC_JOB_TEXT)) + 1
    repeated = (REALISTIC_JOB_TEXT + "\n\n") * repeat_count
    return repeated[:target_length]


async def execute_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Thực thi một request và đo lường thời gian phản hồi chính xác."""
    start = time.perf_counter()
    try:
        response = await client.request(method, url, json=json_data, headers=headers)
        elapsed = time.perf_counter() - start
        return {
            "status_code": response.status_code,
            "elapsed_seconds": elapsed,
            "success": response.is_success,
            "data": response.json() if response.status_code in (200, 201) else None,
            "retry_after": response.headers.get("Retry-After"),
            "error": None,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return {
            "status_code": 0,
            "elapsed_seconds": elapsed,
            "success": False,
            "data": None,
            "retry_after": None,
            "error": f"{type(exc).__name__}: {str(exc)}",
        }


async def run_analysis_benchmark(
    base_url: str,
    concurrency: int,
    total_requests: int,
    text_length: int,
) -> Dict[str, Any]:
    """Chạy kịch bản đo tải phân tích tin tuyển dụng (Rule-Only)."""
    text = generate_text_payload(text_length)
    payload = {"text": text, "use_ai": False}
    url = f"{base_url.rstrip('/')}/api/v1/analyses"

    semaphore = asyncio.Semaphore(concurrency)
    results = []

    start_total = time.perf_counter()

    async def worker():
        async with semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await execute_request(client, "POST", url, json_data=payload)
                results.append(res)

    tasks = [worker() for _ in range(total_requests)]
    await asyncio.gather(*tasks)

    total_time = time.perf_counter() - start_total
    latencies = [r["elapsed_seconds"] for r in results if r["success"]]
    success_count = sum(1 for r in results if r["success"])
    error_count = total_requests - success_count

    p50 = statistics.median(latencies) if latencies else 0.0
    p90 = statistics.quantiles(latencies, n=10)[8] if len(latencies) >= 10 else (max(latencies) if latencies else 0.0)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0.0)
    p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else (max(latencies) if latencies else 0.0)

    return {
        "scenario": "Text Analysis (Rule-Only)",
        "total_requests": total_requests,
        "concurrency": concurrency,
        "text_length_chars": len(text),
        "total_duration_seconds": round(total_time, 3),
        "throughput_rps": round(total_requests / total_time, 2) if total_time > 0 else 0,
        "sample_count": len(results),
        "success_count": success_count,
        "error_count": error_count,
        "error_rate_pct": round((error_count / total_requests) * 100, 2) if total_requests else 100.0,
        "latency_min_s": round(min(latencies), 4) if latencies else 0,
        "latency_mean_s": round(statistics.mean(latencies), 4) if latencies else 0,
        "latency_p50_s": round(p50, 4),
        "latency_p90_s": round(p90, 4),
        "latency_p95_s": round(p95, 4),
        "latency_p99_s": round(p99, 4),
        "latency_max_s": round(max(latencies), 4) if latencies else 0,
        "meets_target_p95": bool(latencies) and error_count == 0 and p95 < 3.0,
    }


async def run_verification_benchmark(
    base_url: str,
    concurrency: int,
    total_requests: int,
) -> Dict[str, Any]:
    """Chạy kịch bản đo tải đối chiếu kho nguồn doanh nghiệp."""
    url = f"{base_url.rstrip('/')}/api/v1/verifications"
    payload = {
        "company_name": "Công ty E2E A",
        "contact_email": "contact@e2e-a.example",
        "recruitment_website": "https://e2e-a.example/careers",
    }
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    start_total = time.perf_counter()

    async def worker():
        async with semaphore:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await execute_request(client, "POST", url, json_data=payload)
                results.append(res)

    tasks = [worker() for _ in range(total_requests)]
    await asyncio.gather(*tasks)

    total_time = time.perf_counter() - start_total
    latencies = [r["elapsed_seconds"] for r in results if r["success"]]
    success_count = sum(1 for r in results if r["success"])
    error_count = total_requests - success_count

    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0.0)

    return {
        "scenario": "Employer Verification",
        "total_requests": total_requests,
        "concurrency": concurrency,
        "total_duration_seconds": round(total_time, 3),
        "throughput_rps": round(total_requests / total_time, 2) if total_time > 0 else 0,
        "sample_count": len(results),
        "success_count": success_count,
        "error_count": error_count,
        "error_rate_pct": round((error_count / total_requests) * 100, 2) if total_requests else 100.0,
        "latency_min_s": round(min(latencies), 4) if latencies else 0,
        "latency_mean_s": round(statistics.mean(latencies), 4) if latencies else 0,
        "latency_p50_s": round(p50, 4),
        "latency_p95_s": round(p95, 4),
        "latency_max_s": round(max(latencies), 4) if latencies else 0,
        "meets_target_p95": bool(latencies) and error_count == 0 and p95 < 1.0,
    }


async def test_payload_limits(base_url: str) -> Dict[str, Any]:
    """Kiểm tra giới hạn dung lượng: gửi > 10.000 ký tự phải bị từ chối 422."""
    url = f"{base_url.rstrip('/')}/api/v1/analyses"
    oversized_text = "A" * 10001
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await execute_request(client, "POST", url, json_data={"text": oversized_text})
    rejected_properly = res["status_code"] in (413, 422)
    return {
        "scenario": "Payload Limit Enforcement (>10k chars)",
        "status_code": res["status_code"],
        "rejected_properly": rejected_properly,
    }


async def test_rate_limiting(base_url: str) -> Dict[str, Any]:
    """Check 10 successes then 429; wait once for a dirty IP window, at most 61s."""
    url = f"{base_url.rstrip('/')}/api/v1/analyses"
    payload = {"text": "Kiểm tra giới hạn tần suất gửi tin tuyển dụng.", "use_ai": False}
    total_probed = 0
    wait_seconds = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(2):
            first_request_started = 0.0
            status_codes = []
            retry_after = None
            for probe_idx in range(11):
                request_started = time.monotonic()
                if probe_idx == 0:
                    first_request_started = request_started
                res = await execute_request(client, "POST", url, json_data=payload)
                total_probed += 1
                status_code = res["status_code"]
                status_codes.append(status_code)

                if status_code == 429:
                    try:
                        retry_after = int(res.get("retry_after") or "")
                    except (TypeError, ValueError):
                        retry_after = None
                    if probe_idx == 10:
                        probe_elapsed = max(0.0, request_started - first_request_started)
                        window_estimate = probe_elapsed + (retry_after or 0)
                        proper = (
                            all(200 <= code < 300 for code in status_codes[:10])
                            and retry_after is not None
                            and 1 <= retry_after <= 61
                            and retry_after_matches_window(retry_after, probe_elapsed)
                        )
                        return {
                            "scenario": "Rate Limiting Enforcement (10 req/60s/IP)",
                            "rate_limited_properly": proper,
                            "total_probed": total_probed,
                            "status_sequence": status_codes,
                            "retry_after_seconds": retry_after,
                            "retry_after_window_seconds": round(window_estimate, 3),
                            "clean_window_wait_seconds": wait_seconds,
                        }
                    if attempt == 0 and retry_after is not None and 1 <= retry_after <= 61:
                        await asyncio.sleep(61)
                        wait_seconds += 61
                        break
                    return {
                        "scenario": "Rate Limiting Enforcement (10 req/60s/IP)",
                        "rate_limited_properly": False,
                        "total_probed": total_probed,
                        "status_sequence": status_codes,
                        "retry_after_seconds": retry_after,
                        "clean_window_wait_seconds": wait_seconds,
                    }

                if not res["success"]:
                    return {
                        "scenario": "Rate Limiting Enforcement (10 req/60s/IP)",
                        "rate_limited_properly": False,
                        "total_probed": total_probed,
                        "status_sequence": status_codes,
                        "retry_after_seconds": None,
                        "clean_window_wait_seconds": wait_seconds,
                    }

                if probe_idx == 10:
                    return {
                        "scenario": "Rate Limiting Enforcement (10 req/60s/IP)",
                        "rate_limited_properly": False,
                        "total_probed": total_probed,
                        "status_sequence": status_codes,
                        "retry_after_seconds": None,
                        "clean_window_wait_seconds": wait_seconds,
                    }

    return {
        "scenario": "Rate Limiting Enforcement (10 req/60s/IP)",
        "rate_limited_properly": False,
        "total_probed": total_probed,
        "status_sequence": [],
        "retry_after_seconds": None,
        "clean_window_wait_seconds": wait_seconds,
    }


def retry_after_matches_window(retry_after: int, elapsed_seconds: float) -> bool:
    # The backend rounds remaining time up by one second; allow two seconds for scheduling skew.
    estimate = retry_after + elapsed_seconds
    return (
        RATE_LIMIT_WINDOW_SECONDS - RATE_LIMIT_WINDOW_TOLERANCE_SECONDS
        <= estimate
        <= RATE_LIMIT_WINDOW_SECONDS + 1 + RATE_LIMIT_WINDOW_TOLERANCE_SECONDS
    )


async def clear_rate_limit_window(base_url: str) -> Dict[str, Any]:
    """Drain the current IP quota, then wait 61s after the 429 to clear its full window."""
    url = f"{base_url.rstrip('/')}/api/v1/analyses"
    payload = {"text": "Rate-window reset probe.", "use_ai": False}
    total_probed = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        for _ in range(11):
            res = await execute_request(client, "POST", url, json_data=payload)
            total_probed += 1
            if res["status_code"] == 429:
                try:
                    retry_after = int(res.get("retry_after") or "")
                except (TypeError, ValueError):
                    retry_after = None
                if retry_after is None or not 1 <= retry_after <= 61:
                    return {"clean": False, "total_probed": total_probed, "wait_seconds": 0}
                await asyncio.sleep(61)
                return {"clean": True, "total_probed": total_probed, "wait_seconds": 61}
            if not res["success"]:
                return {"clean": False, "total_probed": total_probed, "wait_seconds": 0}

    return {"clean": False, "total_probed": total_probed, "wait_seconds": 0}


def evaluate_acceptance_checks(analysis, verification, payload_limit, rate_limit):
    analysis_samples_ok = (
        analysis["total_requests"] > 0
        and analysis["sample_count"] == analysis["total_requests"]
        and analysis["success_count"] == analysis["total_requests"]
        and analysis["error_count"] == 0
    )
    verification_samples_ok = (
        verification["total_requests"] > 0
        and verification["sample_count"] == verification["total_requests"]
        and verification["success_count"] == verification["total_requests"]
        and verification["error_count"] == 0
    )
    return {
        "analysis_samples": analysis_samples_ok,
        "analysis_error_rate": analysis_samples_ok and analysis["error_rate_pct"] == 0,
        "analysis_throughput": analysis_samples_ok and analysis["throughput_rps"] > 5,
        "analysis_p50": analysis_samples_ok and analysis["latency_p50_s"] < 1.0,
        "analysis_p90": analysis_samples_ok and analysis["latency_p90_s"] < 2.0,
        "analysis_p95": analysis_samples_ok and analysis["meets_target_p95"] and analysis["latency_p95_s"] < 3.0,
        "analysis_max": analysis_samples_ok and analysis["latency_max_s"] < 5.0,
        "verification_samples": verification_samples_ok,
        "verification_error_rate": verification_samples_ok and verification["error_rate_pct"] == 0,
        "verification_throughput": verification_samples_ok and verification["throughput_rps"] > 10,
        "verification_p50": verification_samples_ok and verification["latency_p50_s"] < 0.2,
        "verification_p95": verification_samples_ok and verification["meets_target_p95"] and verification["latency_p95_s"] < 1.0,
        "payload_limit": payload_limit,
        "rate_limit": rate_limit,
    }


async def main():
    parser = argparse.ArgumentParser(description="JobShield Load & Performance Benchmark Tool")
    parser.add_argument("--target", default="http://127.0.0.1:8000", help="Target API Base URL")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent workers (default: 5)")
    parser.add_argument("--total-requests", type=int, default=10, help="Total requests to execute per benchmark (default: 10)")
    parser.add_argument("--text-length", type=int, default=5000, help="Text length in chars (default: 5000, max: 10000)")
    parser.add_argument("--output", help="Optional path to output markdown report")
    args = parser.parse_args()

    if args.concurrency < 1 or args.total_requests < 1 or args.text_length < 1:
        print("[ERROR] concurrency, total-requests, and text-length must be positive")
        return 2

    print("=================================================================")
    print("      JobShield R6.1 Performance & Load Testing Benchmark        ")
    print(f" Target: {args.target}")
    print(f" Concurrency: {args.concurrency} workers")
    print(f" Total Requests: {args.total_requests}")
    print(f" Text Length: {args.text_length} chars")
    print("=================================================================\n")

    # Check readiness before running any load against the target.
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            health = await client.get(f"{args.target.rstrip('/')}/ready")
            body = health.json() if health.status_code == 200 else {}
            if (health.status_code != 200 or body.get("status") != "ready"
                    or body.get("database") != "connected" or body.get("schema") != "current"):
                print(f"[ERROR] Target not ready: status {health.status_code}, readiness={body.get('status', 'unknown')}")
                return 1
            print("[INFO] Target /ready OK (DB connected, schema current)")
        except Exception as e:
            print(f"[ERROR] Cannot connect to {args.target}: {e}")
            return 1

    # Run analysis benchmark.
    print("\n[1/4] Đang chạy kiểm thử tải Analysis (Rule-Only)...")
    analysis_res = await run_analysis_benchmark(
        args.target, args.concurrency, args.total_requests, min(args.text_length, 10000)
    )
    print(f"  - Throughput: {analysis_res['throughput_rps']} RPS")
    print(f"  - Latency p50: {analysis_res['latency_p50_s']}s | p95: {analysis_res['latency_p95_s']}s | Max: {analysis_res['latency_max_s']}s")
    print(f"  - Error Rate: {analysis_res['error_rate_pct']}% ({analysis_res['success_count']}/{analysis_res['total_requests']} OK)")
    print(f"  - Mục tiêu p95 < 3.0s: {'ĐẠT (PASS)' if analysis_res['meets_target_p95'] else 'KHÔNG ĐẠT (FAIL)'}")

    # Run verification benchmark.
    print("\n[2/4] Đang chạy kiểm thử tải Verification (Employer Lookups)...")
    verify_res = await run_verification_benchmark(args.target, args.concurrency, args.total_requests)
    print(f"  - Throughput: {verify_res['throughput_rps']} RPS")
    print(f"  - Latency p50: {verify_res['latency_p50_s']}s | p95: {verify_res['latency_p95_s']}s")
    print(f"  - Error Rate: {verify_res['error_rate_pct']}%")

    # Leave a clean window for the payload and rate-limit checks after the load sample.
    rate_window = await clear_rate_limit_window(args.target)
    print(f"\n[RATE WINDOW] Sạch: {'có' if rate_window['clean'] else 'không'}")
    if rate_window["wait_seconds"]:
        print(f"  - Chờ {rate_window['wait_seconds']}s để làm mới cửa sổ kiểm tra")

    # Check payload limit.
    print("\n[3/4] Đang kiểm tra giới hạn kích thước văn bản (>10.000 ký tự)...")
    limit_res = await test_payload_limits(args.target)
    limit_res["rejected_properly"] = limit_res["rejected_properly"] and rate_window["clean"]
    print(f"  - Status code: {limit_res['status_code']} -> {'ĐẠT (Từ chối đúng quy định)' if limit_res['rejected_properly'] else 'LỖI'}")

    # The rate-limit test runs last; its early 429 probe handles the payload test's one request.
    print("\n[4/4] Đang kiểm tra giới hạn tần suất (Rate Limiting - 10 req/60s/IP)...")
    rate_res = await test_rate_limiting(args.target)
    print(f"  - Đã gửi {rate_res['total_probed']} requests -> {'ĐẠT' if rate_res['rate_limited_properly'] else 'LỖI'}")
    if rate_res["clean_window_wait_seconds"]:
        print(f"  - Chờ {rate_res['clean_window_wait_seconds']}s để làm mới cửa sổ kiểm tra")

    acceptance_checks = evaluate_acceptance_checks(
        analysis_res, verify_res, limit_res["rejected_properly"], rate_res["rate_limited_properly"]
    )
    print("\n[ACCEPTANCE] Threshold results:")
    for name, passed in acceptance_checks.items():
        print(f"  - {name}: {'PASS' if passed else 'FAIL'}")
    all_checks_passed = all(acceptance_checks.values())

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target": args.target,
        "concurrency": args.concurrency,
        "analysis_benchmark": analysis_res,
        "verification_benchmark": verify_res,
        "payload_limit_check": limit_res,
        "rate_window_reset": rate_window,
        "rate_limiting_check": rate_res,
        "acceptance_checks": acceptance_checks,
        "all_checks_passed": all_checks_passed,
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_content = f"""# JobShield R6.1 Performance & Load Testing Report

- **Thời điểm thực hiện:** {report['timestamp']}
- **Môi trường đo đạc:** `{args.target}`
- **Mức đồng thời (Concurrency):** {args.concurrency} concurrent requests
- **Kích thước tin kiểm thử:** {analysis_res['text_length_chars']} ký tự (chuẩn 10.000 ký tự tối đa)
- **Kết quả acceptance:** **{'PASS' if all_checks_passed else 'FAIL'}**
- **Cửa sổ rate limit trước giới hạn payload:** {'sạch' if rate_window['clean'] else 'không sạch'} sau {rate_window['total_probed']} probes; chờ {rate_window['wait_seconds']}s

## 1. Kết quả kiểm thử tải Phân tích văn bản (Text Analysis - Rule Only)

| Chỉ số đo lường | Giá trị thực tế | Ngưỡng cam kết (Mục 6.2) | Kết luận |
| :--- | :--- | :--- | :--- |
| **Tổng số request** | {analysis_res['total_requests']} | Baseline đồng thời | {'PASS' if acceptance_checks['analysis_samples'] else 'FAIL'} |
| **Số request thành công** | {analysis_res['success_count']} | Tất cả request | {'PASS' if acceptance_checks['analysis_samples'] else 'FAIL'} |
| **Tỷ lệ lỗi (Error Rate)** | {analysis_res['error_rate_pct']}% | 0% | {'PASS' if acceptance_checks['analysis_error_rate'] else 'FAIL'} |
| **Thông lượng (Throughput)** | {analysis_res['throughput_rps']} req/s | > 5 req/s | {'PASS' if acceptance_checks['analysis_throughput'] else 'FAIL'} |
| **Độ trễ trung vị (p50)** | {analysis_res['latency_p50_s']} giây | < 1.0 giây | {'PASS' if acceptance_checks['analysis_p50'] else 'FAIL'} |
| **Độ trễ p90** | {analysis_res['latency_p90_s']} giây | < 2.0 giây | {'PASS' if acceptance_checks['analysis_p90'] else 'FAIL'} |
| **Độ trễ p95** | **{analysis_res['latency_p95_s']} giây** | **< 3.0 giây** | **{'PASS' if acceptance_checks['analysis_p95'] else 'FAIL'}** |
| **Độ trễ tối đa (Max)** | {analysis_res['latency_max_s']} giây | < 5.0 giây | {'PASS' if acceptance_checks['analysis_max'] else 'FAIL'} |

## 2. Kết quả kiểm thử tải Đối chiếu doanh nghiệp (Employer Verification)

| Chỉ số đo lường | Giá trị thực tế | Ngưỡng cam kết | Kết luận |
| :--- | :--- | :--- | :--- |
| **Tổng số request** | {verify_res['total_requests']} | Baseline đồng thời | {'PASS' if acceptance_checks['verification_samples'] else 'FAIL'} |
| **Số request thành công** | {verify_res['success_count']} | Tất cả request | {'PASS' if acceptance_checks['verification_samples'] else 'FAIL'} |
| **Tỷ lệ lỗi (Error Rate)** | {verify_res['error_rate_pct']}% | 0% | {'PASS' if acceptance_checks['verification_error_rate'] else 'FAIL'} |
| **Thông lượng (Throughput)** | {verify_res['throughput_rps']} req/s | > 10 req/s | {'PASS' if acceptance_checks['verification_throughput'] else 'FAIL'} |
| **Độ trễ trung vị (p50)** | {verify_res['latency_p50_s']} giây | < 0.2 giây | {'PASS' if acceptance_checks['verification_p50'] else 'FAIL'} |
| **Độ trễ p95** | **{verify_res['latency_p95_s']} giây** | **< 1.0 giây** | **{'PASS' if acceptance_checks['verification_p95'] else 'FAIL'}** |

## 3. Kiểm tra ranh giới bảo vệ tải và kích thước

- **Giới hạn 10.000 ký tự:** Gửi payload 10.001 ký tự nhận mã HTTP `{limit_res['status_code']}` (`{'PASS' if acceptance_checks['payload_limit'] else 'FAIL'}`).
- **Rate limit:** HTTP sequence `{rate_res['status_sequence']}`, Retry-After `{str(rate_res['retry_after_seconds']) + 's' if rate_res['retry_after_seconds'] is not None else 'missing'}` (`{'PASS' if acceptance_checks['rate_limit'] else 'FAIL'}`).
"""
        out_path.write_text(md_content, encoding="utf-8")
        print(f"\n[DONE] Đã lưu báo cáo hiệu năng tại: {out_path}")

    return 0 if all_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
