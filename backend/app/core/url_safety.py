"""URL safety and SSRF (Server-Side Request Forgery) protection.

Bảo vệ truy cập URL công khai:
- Chỉ cho phép giao thức HTTP/HTTPS.
- Cấm userinfo (user:pass).
- Chỉ cho phép cổng chuẩn (80, 443).
- Ngăn chặn triệt để SSRF tới mạng nội bộ, loopback, link-local, multicast, và cloud metadata.
- Phân giải DNS và kiểm tra toàn bộ địa chỉ IP được trả về.
"""

import ipaddress
import socket
from typing import List, Tuple
from urllib.parse import urlparse

# Cổng cho phép
ALLOWED_PORTS = {80, 443}

# Tên miền mạng nội bộ bị cấm tuyệt đối
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}

# Hậu tố tên miền nội bộ
BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home",
    ".corp",
)

class URLSafetyError(Exception):
    """Lỗi an toàn URL hoặc vi phạm bảo vệ SSRF."""

    def __init__(self, message_vi: str, code: str = "UNSAFE_URL"):
        super().__init__(message_vi)
        self.message_vi = message_vi
        self.code = code


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Kiểm tra xem địa chỉ IP có thuộc dải mạng nội bộ hoặc bị hạn chế không."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True

    return not ip.is_global or ip.is_multicast or ip.is_reserved


def validate_url_safety(url: str) -> Tuple[str, List[str]]:
    """Xác thực tính an toàn của URL trước khi thực hiện truy vấn HTTP.

    Returns:
        Tuple[str, List[str]]: (normalized_url, resolved_ip_list)

    Raises:
        URLSafetyError: Nếu URL vi phạm quy định an toàn hoặc trỏ tới mạng nội bộ.
    """
    if not url or not isinstance(url, str) or not url.strip():
        raise URLSafetyError(
            "URL không được để trống.",
            code="EMPTY_URL",
        )

    url_clean = url.strip()
    if len(url_clean) > 2048:
        raise URLSafetyError(
            "Độ dài URL vượt quá giới hạn 2048 ký tự.",
            code="URL_TOO_LONG",
        )

    try:
        parsed = urlparse(url_clean)
    except Exception as exc:
        raise URLSafetyError(
            "Định dạng URL không hợp lệ.",
            code="INVALID_URL_FORMAT",
        ) from exc

    # 1. Scheme check
    if parsed.scheme.lower() not in ("http", "https"):
        raise URLSafetyError(
            "Chỉ hỗ trợ giao thức HTTP hoặc HTTPS.",
            code="UNSUPPORTED_SCHEME",
        )

    # 2. Userinfo check
    if parsed.username or parsed.password:
        raise URLSafetyError(
            "URL chứa thông tin xác thực người dùng (userinfo) không được phép.",
            code="USERINFO_NOT_ALLOWED",
        )

    hostname = parsed.hostname
    if not hostname:
        raise URLSafetyError(
            "URL thiếu tên miền hoặc máy chủ hợp lệ.",
            code="MISSING_HOSTNAME",
        )

    hostname_lower = hostname.lower()

    # 3. Port check
    try:
        port = parsed.port
    except ValueError as exc:
        raise URLSafetyError("Cổng URL không hợp lệ.", code="UNSUPPORTED_PORT") from exc
    if port is None:
        port = 443 if parsed.scheme.lower() == "https" else 80
    if port not in ALLOWED_PORTS:
        raise URLSafetyError(
            f"Cổng {port} không được hỗ trợ. Chỉ cho phép cổng 80 hoặc 443.",
            code="UNSUPPORTED_PORT",
        )

    # 4. Blocked hostname strings and suffixes
    if hostname_lower in BLOCKED_HOSTNAMES or any(
        hostname_lower.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES
    ):
        raise URLSafetyError(
            "Truy cập vào tên miền nội bộ hoặc cục bộ bị từ chối.",
            code="SSRF_BLOCKED_HOST",
        )

    # 5. Direct IP check
    try:
        direct_ip = ipaddress.ip_address(hostname_lower)
        if is_ip_private_or_restricted(str(direct_ip)):
            raise URLSafetyError(
                "Địa chỉ IP thuộc dải mạng nội bộ hoặc riêng tư bị chặn (SSRF).",
                code="SSRF_PRIVATE_IP",
            )
        return url_clean, [str(direct_ip)]
    except ValueError:
        # Hostname là tên miền, không phải direct IP
        pass

    # 7. DNS resolution and resolved IP validation
    resolved_ips: List[str] = []
    try:
        addr_info = socket.getaddrinfo(
            hostname,
            port,
            proto=socket.IPPROTO_TCP,
        )
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            resolved_ips.append(ip_str)
    except socket.gaierror as exc:
        raise URLSafetyError(
            f"Không thể phân giải tên miền '{hostname}'.",
            code="DNS_RESOLUTION_FAILED",
        ) from exc

    if not resolved_ips:
        raise URLSafetyError(
            f"Không tìm thấy địa chỉ IP cho tên miền '{hostname}'.",
            code="DNS_NO_IP",
        )

    # Kiểm tra mọi IP được phân giải
    for resolved_ip in resolved_ips:
        if is_ip_private_or_restricted(resolved_ip):
            raise URLSafetyError(
                f"Tên miền phân giải về địa chỉ IP nội bộ bị chặn (SSRF protection).",
                code="SSRF_RESOLVED_PRIVATE_IP",
            )

    return url_clean, resolved_ips
