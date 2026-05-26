"""Simple in-memory rate limiting (single-process; sufficient for MVP register)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import Request

_REGISTER_MAX = 5
_REGISTER_WINDOW_SEC = 15 * 60


class _WindowLimiter:
    def __init__(self, max_attempts: int, window_sec: int) -> None:
        self._max = max_attempts
        self._window = window_sec
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            times = [t for t in self._hits[key] if now - t < self._window]
            if len(times) >= self._max:
                self._hits[key] = times
                return False
            times.append(now)
            self._hits[key] = times
            return True

    def retry_after_sec(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            times = [t for t in self._hits[key] if now - t < self._window]
            if not times:
                return 0
            oldest = min(times)
            return max(1, int(self._window - (now - oldest)) + 1)


_register_limiter = _WindowLimiter(_REGISTER_MAX, _REGISTER_WINDOW_SEC)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return "unknown"


def register_attempt_allowed(request: Request) -> bool:
    return _register_limiter.allow(f"register:{client_ip(request)}")


def register_retry_after_sec(request: Request) -> int:
    return _register_limiter.retry_after_sec(f"register:{client_ip(request)}")
