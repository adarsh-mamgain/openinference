"""Per-route health tracking.

Routes record successes and failures as they serve requests. A route that has
failed recently is deprioritized (and eventually disabled for a cooldown window)
so the router doesn't keep sending work to a broken backend. In-process and
single-node — in production you'd back this with a distributed store.
"""

import threading
import time
from collections import defaultdict, deque


class RouteHealth:
    """Tracks success/failure for a set of routes, with cooldown support."""

    def __init__(
        self,
        window: int = 100,
        fail_threshold: float = 0.5,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.window = window
        self.fail_threshold = fail_threshold
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        self._outcomes: dict[str, deque[bool]] = defaultdict(
            lambda: deque(maxlen=self.window)
        )
        self._cooldown_until: dict[str, float] = {}

    def record(self, route_id: str, ok: bool) -> None:
        with self._lock:
            self._outcomes[route_id].append(ok)
            if ok:
                self._cooldown_until.pop(route_id, None)
            elif self.error_rate(route_id, _locked=True) >= self.fail_threshold:
                # Route is failing badly: start a cooldown.
                self._cooldown_until[route_id] = time.monotonic() + self.cooldown_seconds

    def error_rate(self, route_id: str, _locked: bool = False) -> float:
        outcomes = self._outcomes.get(route_id)
        if not outcomes:
            return 0.0
        return sum(1 for o in outcomes if not o) / len(outcomes)

    def in_cooldown(self, route_id: str, _locked: bool = False) -> bool:
        def _check() -> bool:
            until = self._cooldown_until.get(route_id, 0.0)
            return time.monotonic() < until

        if _locked:
            return _check()
        with self._lock:
            return _check()

    def healthy(self, route_id: str) -> bool:
        with self._lock:
            if self.in_cooldown(route_id, _locked=True):
                return False
            return self.error_rate(route_id, _locked=True) < self.fail_threshold

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {
                rid: {
                    "samples": len(out),
                    "error_rate": round(
                        (sum(1 for o in out if not o) / len(out)) if out else 0.0, 3
                    ),
                    "cooldown": self._cooldown_until.get(rid, 0.0) > time.monotonic(),
                }
                for rid, out in self._outcomes.items()
            }
