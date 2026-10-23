"""
Simple sliding-window rate limiter for sensitive endpoints (login, OTP).

The counters live in process memory, so limits apply per worker process.
Run a single worker, or move the store to Redis, before scaling out.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:

    def __init__(self, *, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise HTTPException(
                    status_code=429,
                    detail="Too many attempts. Please try again later.",
                )
            hits.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


def client_ip(request: Request) -> str:
    # Uses the socket address. X-Forwarded-For is only honoured by uvicorn for proxies
    # listed in FORWARDED_ALLOW_IPS, so clients cannot spoof their way past the limits.
    return request.client.host if request.client else "unknown"


admin_login_limiter = RateLimiter(limit=10, window_seconds=15 * 60)
otp_send_limiter = RateLimiter(limit=5, window_seconds=15 * 60)  # per email address
otp_send_ip_limiter = RateLimiter(limit=30, window_seconds=15 * 60)  # per client IP (shared offices/NAT)
otp_verify_limiter = RateLimiter(limit=20, window_seconds=15 * 60)
