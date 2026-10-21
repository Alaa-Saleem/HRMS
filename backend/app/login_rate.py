"""Simple in-memory sliding-window rate limit for login (per server process)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, status

_lock = threading.Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def reset_login_rate_state() -> None:
    """Clear counters (used by tests / dev only)."""
    with _lock:
        _hits.clear()


def enforce_login_rate(ip: str, *, max_requests: int, window_seconds: float) -> None:
    """Raise 429 when this IP has exceeded max_requests within window_seconds."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _hits[ip]
        bucket[:] = [t for t in bucket if t >= cutoff]
        if len(bucket) >= max_requests:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many login attempts. Try again later.",
            )
        bucket.append(now)
