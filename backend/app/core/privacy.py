"""Privacy safeguards for JobShield.

Đảm bảo:
- Cache-Control: no-store trên tất cả phản hồi phân tích và trích xuất.
- Không ghi log nội dung văn bản thô, tệp ảnh hoặc URL có tham số nhạy cảm.
- Sanitize thông báo lỗi trước khi trả về client.
"""

from typing import Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

SENSITIVE_PARAM_NAMES = {
    "token",
    "auth",
    "key",
    "api_key",
    "apikey",
    "secret",
    "password",
    "pass",
    "credential",
    "session",
    "access_token",
}


def get_privacy_headers() -> Dict[str, str]:
    """Trả về headers HTTP bắt buộc để chống lưu cache kết quả chứa dữ liệu người dùng."""
    return {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
    }


def sanitize_url_for_logging(url: str) -> str:
    """Lược bỏ các tham số query nhạy cảm trong URL trước khi ghi log."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if not parsed.query:
            # Loại bỏ userinfo nếu có
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, "", parsed.fragment))

        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_params = []
        for key, val in query_params:
            if key.lower() in SENSITIVE_PARAM_NAMES:
                sanitized_params.append((key, "[REDACTED]"))
            else:
                sanitized_params.append((key, val))

        clean_query = urlencode(sanitized_params)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, clean_query, parsed.fragment))
    except Exception:
        return "[UNPARSEABLE_URL]"
