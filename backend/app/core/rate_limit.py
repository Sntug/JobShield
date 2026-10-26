"""In-memory rate limiter baseline for anonymous endpoints.

Bảo vệ endpoint POST khỏi spam với sliding window per-IP thread-safe,
dùng OrderedDict giới hạn cứng số lượng IP để chống tràn bộ nhớ kể cả khi bị flood IP.
"""

from collections import OrderedDict
import threading
import time
from typing import List
from fastapi import HTTPException, Request, status

# ponytail: in-memory rate limiter per worker process; trần thiết kế là đa tiến trình cần Redis/centralized store.
_lock = threading.Lock()
_request_history: OrderedDict[str, List[float]] = OrderedDict()

MAX_REQUESTS_PER_WINDOW = 10
WINDOW_SECONDS = 60.0
MAX_TRACKED_IPS = 5000


def get_client_ip(request: Request) -> str:
    """Lấy IP từ request.client.host đã được ASGI proxy middleware phân giải an toàn.

    Tuyệt đối không parse X-Forwarded-For tùy ý từ client để chống bypass rate limit.
    """
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def check_rate_limit(request: Request, bucket: str = "analyses") -> None:
    """Kiểm tra giới hạn tần suất request (10 requests / 60 giây / IP).

    Thread-safe, dùng monotonic clock và cap cứng LRU tối đa MAX_TRACKED_IPS.
    """
    ip = f"{bucket}:{get_client_ip(request)}"
    now = time.monotonic()
    window_start = now - WINDOW_SECONDS

    with _lock:
        history = _request_history.get(ip, [])
        # Lọc bỏ các timestamp quá hạn
        history = [ts for ts in history if ts > window_start]

        if len(history) >= MAX_REQUESTS_PER_WINDOW:
            retry_after = int(WINDOW_SECONDS - (now - history[0])) + 1
            _request_history[ip] = history
            _request_history.move_to_end(ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Quá giới hạn tần suất yêu cầu. Vui lòng thử lại sau.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        history.append(now)
        _request_history[ip] = history
        _request_history.move_to_end(ip)

        # Áp dụng cap cứng tuyệt đối (LRU eviction) ngăn chặn flood IP làm tràn RAM
        while len(_request_history) > MAX_TRACKED_IPS:
            _request_history.popitem(last=False)


def reset_rate_limits() -> None:
    """Reset bộ nhớ rate limit (dùng cho test suite)."""
    with _lock:
        _request_history.clear()
