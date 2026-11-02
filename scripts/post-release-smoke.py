#!/usr/bin/env python3
"""JobShield Comprehensive Post-Release Verification & Monitoring Tool (R6.3).

Kiểm tra toàn diện hệ thống sau khi triển khai lên môi trường Live/Production/Staging:
1. Health & DB Readiness (/healthz, /ready).
2. Luồng phân tích văn bản khách & cô lập phiên truy cập (Session Isolation).
3. Luồng đối chiếu nguồn doanh nghiệp (Employer Verification & Provenance).
4. Cảnh báo an toàn công khai & kiểm tra không rò rỉ PII (/warnings).
5. Bảo vệ phân quyền RBAC: chặn 401/403 trên các endpoint quản trị (/admin/*).
6. Kiểm tra ranh giới bảo vệ: Payload limit (>10k ký tự) & AI fallback an toàn.
7. Kiểm tra Security Headers: X-Request-ID, X-Commit-SHA, Cache-Control: no-store.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def is_jobshield_preview(base_url: str) -> bool:
    try:
        parts = urlsplit(base_url)
        return (
            parts.scheme == "https"
            and not parts.username
            and not parts.password
            and not parts.query
            and not parts.fragment
            and parts.path in ("", "/")
            and parts.port is None
            and re.fullmatch(r"job-shield-[a-z0-9-]+-sntug\.vercel\.app", parts.hostname or "") is not None
        )
    except ValueError:
        return False


def request_api(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> Tuple[int, Any, Dict[str, str], float]:
    """Gửi HTTP request và đo lường latency, parse JSON response."""
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "JobShield-PostRelease-Smoke/1.0",
        **(headers or {}),
    }

    bypass_secret = os.environ.get("VERCEL_AUTOMATION_BYPASS_SECRET")
    if bypass_secret and is_jobshield_preview(base_url):
        if len(bypass_secret) > 4096 or any(ord(character) < 33 or ord(character) > 126 for character in bypass_secret):
            return 0, {"error": "Invalid VERCEL_AUTOMATION_BYPASS_SECRET format."}, {}, 0.0
        req_headers["x-vercel-protection-bypass"] = bypass_secret

    req = Request(url, data=data, method=method, headers=req_headers)
    start = time.perf_counter()

    try:
        response = build_opener(NoRedirect).open(req, timeout=timeout)
    except HTTPError as err:
        response = err
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return 0, {"error": str(exc)}, {}, elapsed

    elapsed = time.perf_counter() - start
    with response:
        status_code = response.status
        resp_headers = {k.lower(): v for k, v in response.headers.items()}
        raw_body = response.read(1024 * 1024 + 1)
        try:
            body = json.loads(raw_body) if raw_body else {}
        except Exception:
            body = {"raw": raw_body.decode("utf-8", errors="replace")}
        return status_code, body, resp_headers, elapsed


def run_post_release_checks(target_url: str, expected_sha: Optional[str] = None) -> Dict[str, Any]:
    print("=================================================================")
    print("     JobShield Post-Release Smoke & Monitoring Verification      ")
    print(f" Target URL: {target_url}")
    if expected_sha:
        print(f" Expected Commit SHA: {expected_sha}")
    print("=================================================================\n")

    checks = []

    # 1. Healthz & Commit SHA
    status, body, headers, latency = request_api(target_url, "/healthz")
    passed = status == 200 and "x-request-id" in headers
    if expected_sha is not None:
        commit_sha = headers.get("x-commit-sha")
        passed = passed and bool(commit_sha) and commit_sha == expected_sha[:7]
    checks.append({
        "name": "1. Health Endpoint & Trace Headers (/healthz)",
        "passed": passed,
        "latency_s": round(latency, 4),
        "details": f"HTTP {status}, Commit: {headers.get('x-commit-sha', 'N/A')}, Request-ID: {headers.get('x-request-id', 'N/A')}",
    })
    print(f"[{'PASS' if passed else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s ({checks[-1]['details']})")

    # 2. Database Readiness
    status, body, headers, latency = request_api(target_url, "/ready")
    passed = status == 200 and body.get("status") == "ready" and body.get("database") == "connected" and body.get("schema") == "current"
    checks.append({
        "name": "2. Database Readiness & Schema Current (/ready)",
        "passed": passed,
        "latency_s": round(latency, 4),
        "details": f"Status: {body.get('status')}, Database: {body.get('database')}, Schema: {body.get('schema')}",
    })
    print(f"[{'PASS' if passed else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s ({checks[-1]['details']})")

    # 3. Guest Analysis & Session Isolation
    text_sample = (
        "Công ty Mẫu Thu Phí (DEMO) tuyển Nhân viên nhập liệu. Lương: 8 triệu đồng/tháng. "
        "Yêu cầu: đóng phí tuyển dụng 500.000 đồng để nhận việc. Đặt cọc 1.000.000 đồng trước phỏng vấn."
    )
    status, body, headers, latency = request_api(target_url, "/api/v1/analyses", "POST", {"text": text_sample})
    analysis_id = body.get("id")
    guest_token = body.get("guest_session_token")
    passed_post = status == 201 and analysis_id and guest_token and body.get("risk_label_vi") == "Rủi ro cao"

    # Đọc lại bằng token
    status_get, body_get, _, _ = request_api(target_url, f"/api/v1/analyses/{analysis_id}", headers={"X-Guest-Session-Token": guest_token})
    passed_get = status_get == 200 and body_get.get("id") == analysis_id

    # Đọc không token (phải bị 401 hoặc 404)
    status_anon, _, _, _ = request_api(target_url, f"/api/v1/analyses/{analysis_id}")
    passed_isolation = status_anon in (401, 404)

    checks.append({
        "name": "3. Guest Analysis Flow & Session Token Isolation",
        "passed": passed_post and passed_get and passed_isolation,
        "latency_s": round(latency, 4),
        "details": f"Analysis created: {analysis_id}, Token validated, Anon blocked: HTTP {status_anon}",
    })
    print(f"[{'PASS' if checks[-1]['passed'] else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s")

    # 4. Employer Verification Lookup
    status, body, headers, latency = request_api(
        target_url, "/api/v1/verifications", "POST",
        {"company_name": "Công ty E2E A", "contact_email": "contact@e2e-a.example", "recruitment_website": "https://e2e-a.example/careers"}
    )
    passed_verify = status == 200 and "verification_label_vi" in body
    checks.append({
        "name": "4. Employer Verification Lookup (/api/v1/verifications)",
        "passed": passed_verify,
        "latency_s": round(latency, 4),
        "details": f"Label: {body.get('verification_label_vi')}, Sources count: {len(body.get('matched_sources', []))}",
    })
    print(f"[{'PASS' if passed_verify else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s ({checks[-1]['details']})")

    # 5. Public Safety Warnings & Zero PII Leakage
    status, body, headers, latency = request_api(target_url, "/api/v1/warnings")
    passed_warnings = status == 200 and "items" in body
    # Verify no private emails leaked in warnings
    no_pii = True
    for item in body.get("items", []):
        if "@" in str(item.get("public_summary_vi", "")):
            no_pii = False
    checks.append({
        "name": "5. Public Safety Warnings & PII Sanitization (/api/v1/warnings)",
        "passed": passed_warnings and no_pii,
        "latency_s": round(latency, 4),
        "details": f"Public active warnings: {body.get('total', 0)}, PII redacted: {no_pii}",
    })
    print(f"[{'PASS' if checks[-1]['passed'] else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s")

    # 6. Admin Route Protection (RBAC)
    status, body, headers, latency = request_api(target_url, "/api/v1/admin/reports")
    passed_admin_guard = status in (401, 403)
    checks.append({
        "name": "6. Admin Endpoint Protection (/api/v1/admin/*)",
        "passed": passed_admin_guard,
        "latency_s": round(latency, 4),
        "details": f"Unauthenticated request correctly rejected with HTTP {status}",
    })
    print(f"[{'PASS' if passed_admin_guard else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s ({checks[-1]['details']})")

    # 7. Payload Limit & AI Graceful Fallback
    status, body, headers, latency = request_api(target_url, "/api/v1/analyses", "POST", {"text": "A" * 10001})
    passed_payload_limit = status in (413, 422)

    status_fb, body_fb, _, _ = request_api(target_url, "/api/v1/analyses", "POST", {"text": "Tuyển dụng nhân viên thu ngân.", "use_ai": True, "ai_consent": False})
    passed_ai_fallback = status_fb == 201
    checks.append({
        "name": "7. Payload Limit (>10k chars) & AI Graceful Fallback",
        "passed": passed_payload_limit and passed_ai_fallback,
        "latency_s": round(latency, 4),
        "details": f"Oversized payload rejected (HTTP {status}), No-consent fallback OK (HTTP {status_fb})",
    })
    print(f"[{'PASS' if checks[-1]['passed'] else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s")

    # 8. Privacy Headers
    status, body, headers, latency = request_api(target_url, "/api/v1/auth/login", "POST", {"email": "test@example.com", "password": "wrong"})
    passed_headers = "no-store" in headers.get("cache-control", "").lower()
    checks.append({
        "name": "8. Security Headers (Cache-Control: no-store)",
        "passed": passed_headers,
        "latency_s": round(latency, 4),
        "details": f"Cache-Control: {headers.get('cache-control', 'N/A')}",
    })
    print(f"[{'PASS' if passed_headers else 'FAIL'}] {checks[-1]['name']} - {latency:.3f}s")

    all_passed = all(c["passed"] for c in checks)
    print("\n=================================================================")
    print(f"   KẾT QUẢ KIỂM TRA SAU PHÁT HÀNH: {'ĐẠT (PASS 100%)' if all_passed else 'CÓ LỖI (FAIL)'}")
    print("=================================================================")

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target_url": target_url,
        "expected_sha": expected_sha,
        "all_passed": all_passed,
        "total_checks": len(checks),
        "passed_checks": sum(1 for c in checks if c["passed"]),
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description="JobShield Post-Release Smoke Verification Tool")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of deployed API or Preview")
    parser.add_argument("--sha", help="Expected Git commit SHA")
    parser.add_argument("--output", help="Optional path to output markdown report")
    args = parser.parse_args()

    results = run_post_release_checks(args.url, args.sha)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md = f"""# JobShield Post-Release Smoke Verification Report

- **Thời điểm kiểm tra:** {results['timestamp']}
- **Mục tiêu kiểm thử:** `{results['target_url']}`
- **Commit SHA đối chiếu:** `{results['expected_sha'] or 'N/A'}`
- **Kết quả tổng quát:** **{'ĐẠT (PASS 100%)' if results['all_passed'] else 'KHÔNG ĐẠT (FAIL)'}** ({results['passed_checks']}/{results['total_checks']} tiêu chí đạt)

## Chi tiết kết quả kiểm tra 8 tiêu chí phát hành

| Tiêu chí kiểm tra | Trạng thái | Độ trễ | Ghi chú & Chi tiết kỹ thuật |
| :--- | :---: | :--- | :--- |
"""
        for c in results["checks"]:
            status_badge = "✓ ĐẠT" if c["passed"] else "✗ LỖI"
            md += f"| {c['name']} | {status_badge} | {c['latency_s']}s | {c['details']} |\n"

        summary = "Tất cả các kiểm tra được liệt kê ở trên đã đạt." if results["all_passed"] else "Một hoặc nhiều kiểm tra thất bại; xem bảng chi tiết. Báo cáo này không xác nhận phát hành."
        if results["expected_sha"] is None:
            summary += " SHA không được đối chiếu vì không cung cấp `--sha`."
        md += f"\n## Kết quả\n\n{summary}\n"
        out_path.write_text(md, encoding="utf-8")
        print(f"\n[DONE] Đã lưu báo cáo kiểm tra sau phát hành tại: {out_path}")

    if not results["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
