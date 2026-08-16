"""In-process metrics collection and aggregation for the inference server.

This module records, per request:

* **TTFT** — time-to-first-token. For streaming requests, the wall-clock time
  from dispatch (request received) to the first real content delta. For
  non-streaming requests there is no first token to time, so we record the full
  generation time and it is surfaced separately as ``latency``.
* **TPOT / ITL** — inter-token latency: the gap between consecutive content
  deltas while streaming. Reported as per-token latency.
* **Total latency** — end-to-end request wall-clock time.
* **Token totals** — prompt/completion token counts (from ``usage``).
* **Counters** — number of requests, broken out by HTTP status class.

All state lives behind a single lock so the registry is safe to touch from both
the asyncio event loop (router, generator) and worker threads
(``asyncio.to_thread``). It is intentionally simple and in-process; swap the
backing store for something like Prometheus/Redis when wiring real dashboards.
"""

import threading
import time
from collections import defaultdict


def _percentile(sorted_samples: list[float], q: float) -> float | None:
    """Return the q-th percentile (0-100) of *sorted* samples."""
    if not sorted_samples:
        return None
    if q <= 0:
        return sorted_samples[0]
    if q >= 100:
        return sorted_samples[-1]
    idx = (len(sorted_samples) - 1) * (q / 100.0)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_samples) - 1)
    frac = idx - lo
    return sorted_samples[lo] + (sorted_samples[hi] - sorted_samples[lo]) * frac


class Metrics:
    """Thread-safe registry that accumulates samples and can aggregate them."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, int] = defaultdict(int)  # status-class -> count
        self._total_requests = 0
        self._errors = 0
        self._latency: list[float] = []
        self._ttft: list[float] = []
        self._inter_token: list[float] = []
        self._completion_tokens = 0
        self._prompt_tokens = 0
        self._started = time.monotonic()

    # -- recording --------------------------------------------------------

    def record_request(self, status_code: int) -> None:
        """Record a finished request by HTTP status class."""
        cls = f"{status_code // 100}xx"
        with self._lock:
            self._total_requests += 1
            self._requests[cls] += 1
            if status_code >= 400:
                self._errors += 1

    def record_latency(self, seconds: float) -> None:
        with self._lock:
            self._latency.append(seconds)

    def record_ttft(self, seconds: float) -> None:
        with self._lock:
            self._ttft.append(seconds)

    def record_inter_token(self, seconds: float) -> None:
        with self._lock:
            self._inter_token.append(seconds)

    def record_tokens(self, prompt: int, completion: int) -> None:
        with self._lock:
            self._prompt_tokens += max(0, prompt)
            self._completion_tokens += max(0, completion)

    def reset(self) -> None:
        """Clear all recorded samples (mainly for tests)."""
        with self._lock:
            self._requests.clear()
            self._total_requests = 0
            self._errors = 0
            self._latency = []
            self._ttft = []
            self._inter_token = []
            self._completion_tokens = 0
            self._prompt_tokens = 0
            self._started = time.monotonic()

    # -- aggregation (reads collect under the lock, then compute outside) ---

    def _snapshot(self):
        with self._lock:
            return (
                sorted(self._latency),
                sorted(self._ttft),
                sorted(self._inter_token),
                dict(self._requests),
                self._total_requests,
                self._errors,
                self._prompt_tokens,
                self._completion_tokens,
                self._started,
            )

    def summary(self) -> dict:
        """Return a JSON-serializable report of the current state."""
        lat, ttft, it, req, total, errors, pt, ct, started = self._snapshot()
        n_completed = _dnf(lat)
        uptime = time.monotonic() - started

        def agg(samples: list[float]) -> dict | None:
            if not samples:
                return None
            n = len(samples)
            return {
                "count": n,
                "min": round(samples[0], 6),
                "p50": round(_percentile(samples, 50), 6),
                "p95": round(_percentile(samples, 95), 6),
                "p99": round(_percentile(samples, 99), 6),
                "max": round(samples[-1], 6),
                "mean": round(sum(samples) / n, 6),
            }

        return {
            "uptime_seconds": round(uptime, 2),
            "requests": {
                "total": total,
                "errors": errors,
                "error_rate": round(errors / total, 4) if total else 0.0,
                "by_status": req,
            },
            "latency_ms": agg(lat),
            "ttft_ms": agg(ttft),
            "inter_token_latency_ms": agg(it),
            "tokens": {
                "prompt": pt,
                "completion": ct,
                "total": pt + ct,
            },
            "throughput": {
                "requests_per_sec": round(n_completed / uptime, 4) if uptime else 0.0,
            },
        }


# Module-level singleton shared across the app.
metrics = Metrics()


def _dnf(samples: list[float]) -> int:
    return len(samples)
