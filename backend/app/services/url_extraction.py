"""URL extraction service for public recruitment web pages.

Bảo vệ an toàn:
- Kiểm tra SSRF và DNS trước khi gửi request.
- Giới hạn redirect (tối đa 3 lần) và xác thực an toàn từng URL redirect.
- Không vượt đăng nhập, CAPTCHA hoặc hạn chế quyền truy cập.
- Trích xuất văn bản thuần có ý nghĩa từ HTML bằng HTMLParser chuẩn của Python.
- Giới hạn kích thước tải về tối đa 1 MB để phòng tránh DoS.
"""

import logging
import re
import socket
import threading
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import urljoin

import httpx

from app.core.url_safety import validate_url_safety, URLSafetyError

logger = logging.getLogger("uvicorn.error")

MAX_RESPONSE_BYTES = 1024 * 1024  # 1 MB
MAX_REDIRECTS = 3
DEFAULT_TIMEOUT_SECONDS = 5.0

# Các từ khóa nhận diện trang yêu cầu đăng nhập / CAPTCHA
LOGIN_INDICATORS = [
    "đăng nhập để xem",
    "đăng nhập để tiếp tục",
    "vui lòng đăng nhập",
    "yêu cầu đăng nhập",
    "sign in to continue",
    "log in to view",
    "login required",
    "access denied",
    "security verification",
    "cf-browser-verification",
    "xác minh bạn là con người",
]


@dataclass
class URLExtractionResult:
    """Kết quả trích xuất văn bản từ URL công khai."""

    success: bool
    text: Optional[str] = None
    source_url: str = ""
    failure_vi: Optional[str] = None
    status_code: Optional[int] = None


class VisibleTextHTMLParser(HTMLParser):
    """HTML Parser trích xuất văn bản hiển thị cho người dùng, bỏ qua scripts/styles/nav."""

    def __init__(self):
        super().__init__()
        self._pieces: List[str] = []
        self._ignore_tags = {
            "script",
            "style",
            "noscript",
            "nav",
            "header",
            "footer",
            "svg",
            "title",
            "iframe",
        }
        self._ignore_depth = 0

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() in self._ignore_tags:
            self._ignore_depth += 1
        elif tag.lower() in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self._pieces.append("\n")

    def handle_endtag(self, tag: str):
        if tag.lower() in self._ignore_tags:
            if self._ignore_depth > 0:
                self._ignore_depth -= 1
        elif tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self._pieces.append("\n")

    def handle_data(self, data: str):
        if self._ignore_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self._pieces.append(f" {cleaned} ")

    def get_text(self) -> str:
        raw_text = "".join(self._pieces)
        # Chuẩn hóa khoảng trắng và dòng trống
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw_text.splitlines()]
        clean_lines = [line for line in lines if line]
        return "\n".join(clean_lines)


def is_login_or_captcha_required(html: str) -> bool:
    """Kiểm tra xem nội dung trang có phải là trang chặn đăng nhập hoặc CAPTCHA không."""
    lower_html = html.lower()
    return any(indicator in lower_html for indicator in LOGIN_INDICATORS)


def extract_text_from_url(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    client: Optional[httpx.Client] = None,
) -> URLExtractionResult:
    """Fetch bounded public content; pin every connection to a validated IP."""
    current_url = url

    def failure(message: str, status_code=None) -> URLExtractionResult:
        return URLExtractionResult(False, source_url=current_url, failure_vi=message, status_code=status_code)

    should_close_client = client is None
    if client is None:
        client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=3.0),
            trust_env=False,
            # IP origins may be shared by different TLS hostnames across redirects.
            limits=httpx.Limits(max_keepalive_connections=0),
            headers={"User-Agent": "JobShield/1.0", "Accept-Encoding": "identity"},
        )
    deadline = time.monotonic() + timeout
    connections = []

    def interrupt(connection):
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def enforce_deadline(event, info):
        if event != "connection.connect_tcp.complete":
            return
        connection = info["return_value"].get_extra_info("socket")
        if connection is None:
            return
        # A duplicate still interrupts the connection after TLS detaches the original socket.
        owned = connection.dup()
        remaining = deadline - time.monotonic()
        timer = threading.Timer(max(0, remaining), interrupt, args=(owned,))
        timer.daemon = True
        connections.append((timer, owned))
        if remaining <= 0:
            interrupt(owned)
        else:
            timer.start()

    try:
        for redirect_count in range(MAX_REDIRECTS + 1):
            try:
                current_url, ips = validate_url_safety(current_url)
                original = httpx.URL(current_url)
                pinned = original.copy_with(host=ips[0])
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return failure("Hết thời gian chờ trang nguồn. Vui lòng dán văn bản trực tiếp.")
                with client.stream(
                    "GET", pinned, follow_redirects=False,
                    headers={"Host": original.netloc.decode("ascii"), "Accept-Encoding": "identity"},
                    extensions={"sni_hostname": original.raw_host.decode("ascii"), "trace": enforce_deadline},
                    timeout=httpx.Timeout(remaining, connect=min(3.0, remaining)),
                ) as response:
                    status_code = response.status_code
                    if status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location or redirect_count == MAX_REDIRECTS:
                            return failure("Trang chuyển hướng không hợp lệ hoặc quá nhiều lần.", status_code)
                        current_url = urljoin(current_url, location)
                        continue
                    if status_code in {401, 403}:
                        return failure("Trang yêu cầu đăng nhập hoặc hạn chế quyền truy cập. Vui lòng dán văn bản trực tiếp.", status_code)
                    if status_code >= 400:
                        return failure(f"Trang nguồn trả về lỗi HTTP {status_code}. Vui lòng dán văn bản trực tiếp.", status_code)
                    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                    if content_type not in {"text/html", "text/plain"}:
                        return failure("Định dạng trang không được hỗ trợ (chỉ hỗ trợ HTML hoặc văn bản).", status_code)
                    # Reject compressed responses so a small wire chunk cannot expand without a bound.
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        return failure("Trang nguồn dùng định dạng nén không được hỗ trợ. Vui lòng dán văn bản trực tiếp.", status_code)
                    content_length = response.headers.get("Content-Length", "")
                    if content_length.isdigit() and int(content_length) > MAX_RESPONSE_BYTES:
                        return failure("Nội dung trang vượt giới hạn 1MB. Vui lòng dán văn bản trực tiếp.", status_code)
                    chunks, total = [], 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_RESPONSE_BYTES:
                            return failure("Nội dung trang vượt giới hạn 1MB. Vui lòng dán văn bản trực tiếp.", status_code)
                        if time.monotonic() > deadline:
                            return failure("Hết thời gian chờ trang nguồn. Vui lòng dán văn bản trực tiếp.")
                        chunks.append(chunk)
                    text_content = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
            except URLSafetyError as exc:
                return failure(exc.message_vi)
            except httpx.TimeoutException:
                return failure("Hết thời gian chờ trang nguồn (timeout). Vui lòng dán văn bản trực tiếp.")
            except (httpx.RequestError, httpx.InvalidURL, ValueError):
                return failure("Không thể kết nối hoặc đọc trang nguồn. Vui lòng kiểm tra URL hoặc dán văn bản trực tiếp.")

            if is_login_or_captcha_required(text_content):
                return failure("Trang yêu cầu đăng nhập hoặc xác thực CAPTCHA. Vui lòng dán văn bản trực tiếp.", status_code)
            if content_type == "text/plain":
                clean_text = text_content.strip()
            else:
                parser = VisibleTextHTMLParser()
                parser.feed(text_content)
                clean_text = parser.get_text()
            if len(clean_text) < 15:
                return failure("Không tìm thấy nội dung văn bản tuyển dụng công khai trên trang. Vui lòng dán văn bản trực tiếp.", status_code)
            return URLExtractionResult(True, text=clean_text[:10000], source_url=current_url, status_code=status_code)
        return failure("Trang chuyển hướng quá nhiều lần.")
    finally:
        for timer, connection in connections:
            timer.cancel()
            connection.close()
        if should_close_client:
            client.close()
