# After Week 2 — admission control, and the honest batching gap

This document captures the *first* measurable Week-2 improvement (admission
control, A1) versus the Week-1 baseline, and — honestly — what continuous
batching & prefix caching require but are **not** yet implemented.

## Headline change: the server no longer drowns

### Week 1 baseline: oversubscription kills the box

Under concurrency, the baseline collapsed:

| Concurrency | Behavior |
|-------------|----------|
| 1 | Full success, healthy latency |
| 2 | Streams returned 200 with **zero tokens**; effectively degraded |
| 4 | **Connection errors** (`ConnectError: All connection attempts failed`) — the box couldn't even accept new connections |

The failure mode was nasty: a client that pushed a few concurrent requests both
lost those requests *and* made the whole server unresponsive.

### After admission control: clean, bounded rejection

With `MAX_IN_FLIGHT=2`, firing **8 concurrent** chat requests against the real
model produced:

```
req0: 200   req1: 200   req2: 503   req3: 503
req4: 503   req5: 503   req6: 503   req7: 503
=> accepted: 2, rejected: 503: 6
```

- Exactly **`MAX_IN_FLIGHT` requests are admitted** and served (200).
- The **rest get a prompt 503 + `Retry-After`** instead of hanging or killing
  connectivity.
- The server stays responsive (health/metrics continue to answer).

That is real progress: from "client-driven overload makes the box unresponsive"
to "excess load is rejected with a clear, retryable signal." This is the same
admission-control idea vLLM uses (`--max-num-seqs`, capacity limits) applied at
the scheduler/HTTP boundary.

## How to reproduce

```bash
# terminal 1 — low admission ceiling
cd inference-server
MAX_IN_FLIGHT=2 uv run uvicorn inference_server.main:app --port 8000

# terminal 2 — fire many concurrent requests
uv run --project benchmarks python -m benchmarks.run
```

Or run the included live assertion (`/tmp/run_admission_live.py` pattern, port
`8135`): expects a mix of 200 and 503, passes if admission works.

## What continuous batching & prefix caching still need

See [`../notes/kv-cache-prefill-decode.md`](../notes/kv-cache-prefill-decode.md)
for the theory. The honest status:

| Capability | Status | Blocker |
|------------|--------|---------|
| Admission control (A1) | **Done**, tested, live-verified | — |
| Sequential batch of queued jobs | Partial: scheduler already drains a queue in priority order | Higher *per-request* throughput needs token-level batching |
| Continuous batching (B1/B2) | **Not implemented** | Requires `llama_batch`/multi-sequence API or a custom runtime; the high-level `create_chat_completion` manages a per-request KV cache we can't extend |
| Paged KV cache | **Not implemented** | Same runtime constraint |
| Prefix caching (B3) | **Not implemented** | Same runtime constraint |

So the measurable, correct Week-2 win here is admission control + the
measurement harness to prove it and to quantify the remaining gap. Real
continuous batching is the *next* big milestone and is blocked on switching the
runtime to one that exposes multi-sequence decode — a deliberate, documented
decision rather than a fake batch layer.

## Remaining Week-2 note

The single-client numbers (`docs/benchmarks/baseline.md`) are unchanged by
admission control (it only governs the *overload* case). Re-run
`benchmarks/run.py` with `MAX_IN_FLIGHT` sized above your test concurrency to
compare steady-state latency on the same workload.
