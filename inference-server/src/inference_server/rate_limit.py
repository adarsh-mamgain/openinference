"""In-memory fixed-window rate limiting.

A `RateLimiter` tracks how many requests a key has made in the current time
window and rejects requests that exceed the limit. It is intentionally simple:
no external store, no async locking. In production you would back this with a
distributed store like Redis.

Use it as a dependency. Because the limiter lives on the app state, it is
shared across all requests to the same worker.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _window_start(self, now: float) -> float:
        return now - self.window_seconds

    def allow(self, key: str) -> bool:
        """Record a request for `key` and return whether it is allowed."""
        now = time.monotonic()
        window_start = self._window_start(now)

        # Drop timestamps that have fallen out of the current window.
        timestamps = [t for t in self._requests[key] if t >= window_start]

        if len(timestamps) >= self.max_requests:
            self._requests[key] = timestamps
            return False

        timestamps.append(now)
        self._requests[key] = timestamps
        return True

    def remaining(self, key: str) -> int:
        """Number of requests `key` can still make in this window."""
        now = time.monotonic()
        active = [t for t in self._requests[key] if t >= self._window_start(now)]
        return max(0, self.max_requests - len(active))


def make_rate_limit_dependency(limiter: RateLimiter):
    """Factory that closes over a shared limiter and returns a FastAPI dependency."""

    async def enforce_rate_limit(request: Request) -> None:
        api_key = request.headers.get("authorization", "anonymous")
        if not limiter.allow(api_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(limiter.window_seconds)},
            )

    return enforce_rate_limit
