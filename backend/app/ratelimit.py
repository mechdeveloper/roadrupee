"""Per-IP sliding-window rate limit for the endpoints that call live Claude (trace, explain).

Cached answers and deterministic fallbacks are free; only a call that would reach Claude counts.
In-memory and per process: fine for one small container, and it protects the API key from a runaway client.
"""
from __future__ import annotations

import math
import os
import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse

LIMIT = int(os.environ.get("RATE_LIMIT_PER_MIN", "20"))
WINDOW = 60.0
MAX_TRACKED = 5000  # distinct IPs remembered; the oldest are dropped first


class RateLimiter:
    def __init__(self, limit: int = LIMIT, window: float = WINDOW, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> tuple[bool, int]:
        """(allowed, seconds until the oldest hit leaves the window). Counts the hit when allowed."""
        now = self.clock()
        q = self.hits.setdefault(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False, max(1, math.ceil(self.window - (now - q[0])))
        q.append(now)
        if len(self.hits) > MAX_TRACKED:  # keep memory bounded
            for k in list(self.hits)[: len(self.hits) - MAX_TRACKED]:
                del self.hits[k]
        return True, 0


live = RateLimiter()


def client_ip(request: Request) -> str:
    """The Next.js proxy sets x-client-ip from the ingress's X-Forwarded-For (the backend is internal-only);
    when called directly (dev, tests) fall back to the socket address."""
    return request.headers.get("x-client-ip") or (request.client.host if request.client else "unknown")


def too_many(wait: int) -> JSONResponse:
    return JSONResponse(
        {"error": "rate_limited", "retry_after": wait,
         "message": f"You're asking quickly. Please wait {wait} seconds and try again."},
        status_code=429, headers={"Retry-After": str(wait)},
    )
