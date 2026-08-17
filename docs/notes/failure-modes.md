# Week 4 — Failure modes: what happens when things go wrong

A production inference server is defined by its failure behavior more than its
happy path. This note catalogs every failure mode we harden, the mechanism, and
the measured/verified behavior. Companion proof lives in the test suite.

## The failure catalogue

| Failure mode | Mechanism | Behavior | Where proven |
|--------------|-----------|----------|--------------|
| Overload (too many concurrent requests) | admission control: `in_flight + queued >= max_in_flight` → reject | Clean **503 + `Retry-After: 2`**; box stays responsive | `test_admission.py::test_chat_returns_503_when_at_capacity`; live: 8 concurrent → 2 served, 6 rejected |
| Hung generation (model wedges) | per-job timeout: `wait_for(_execute, job_timeout_seconds)` | Job → `failed`, result `error: timed out after Ns`; worker freed | `test_scheduler.py::test_job_times_out_instead_of_hanging` |
| Stalled stream | timeout closes the job's stream bus | SSE subscriber gets `[DONE]` instead of hanging forever | `test_scheduler.py::test_streaming_job_times_out_and_subscriber_releases` |
| Backend route failure | router health: `error_rate >= 0.5` → 30s cooldown | Router skips the broken route; failed requests retry the next healthy fallback (bounded by `router_max_fallbacks`) | `test_router.py::test_chat_retries_fallback_route`, `test_chat_fallback_respects_max_fallbacks` |
| No eligible route | router raises `ValueError("no eligible route")` | **404** "Model not available on this server" — not a hang, not a 500 | `test_router.py::test_chat_no_eligible_route_returns_404` |
| Missing model weights | `ModelUnavailableError` at boot/first use | Endpoints surface a clear error telling the operator to run `scripts/download-model.sh` | `llm.py::_require` |
| Client disconnect mid-stream | SSE generator detects the stream never reached terminal status | Not counted as a backend failure → health score stays clean | `routers/chat.py::_stream_chat_completion` `finally` |
| Server restart (deploy) | graceful shutdown: drain up to `shutdown_grace_seconds`, then cancel workers + `close_all()` streams | In-flight jobs finish (grace window); any straggler streams release their subscribers instead of hanging | `test_scheduler.py::test_stop_drains_in_flight_then_cancels`, `test_stop_closes_open_streams` |
| Rate limiting | fixed-window counter per key | **429** on burst; by-status counters in `/metrics` show it | `test_rate_limit.py` |

## The two changes that made the difference (this week)

### 1. Per-job timeout (`job_timeout_seconds`)

Before: a model call that never returned held a worker forever and the SSE
reader waited on a stream that never ended. After:

```
worker._run(job):
    wait_for(_execute(job), timeout=job_timeout_seconds)
        ├─ TimeoutError → set job failed, result "error: timed out after Ns"
        │                → close the stream bus (subscribers unblock)
        └─ normal      → completed
```

The worker is freed the moment the timeout fires, so a wedged generation can't
starve the pool. Default: 120s.

### 2. Graceful shutdown + stream cleanup

`stop()` no longer yanks workers instantly. It drains in-flight jobs for
`shutdown_grace_seconds`, then cancels stragglers and `close_all()`s the stream
bus. Deploys no longer leave clients hanging on half-open SSE connections.

## Design principle

Every failure mode resolves to either a **clean, bounded, typed error** (503,
404, 429, job `failed`) or a **documented degradation** (timeout kills one job,
not the box; a flaky client can't poison route health). The test suite is the
proof — 44 tests, including one for each row above.
