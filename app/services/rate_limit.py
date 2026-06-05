from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from time import time

from app.models.control import RateLimitDecision


@dataclass
class InMemoryRateLimiter:
    window_seconds: int = 60
    requests_by_user: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: Lock = field(default_factory=Lock, repr=False)

    def check(self, user_id: str, limit_per_minute: int) -> RateLimitDecision:
        if limit_per_minute <= 0:
            return RateLimitDecision(allowed=True, remaining=limit_per_minute)

        now = time()
        cutoff = now - self.window_seconds

        with self._lock:
            bucket = self.requests_by_user[user_id]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= limit_per_minute:
                retry_after = int(self.window_seconds - (now - bucket[0])) if bucket else self.window_seconds
                return RateLimitDecision(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=max(retry_after, 1),
                )

            bucket.append(now)
            remaining = max(limit_per_minute - len(bucket), 0)
            return RateLimitDecision(allowed=True, remaining=remaining)
