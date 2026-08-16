# Benchmark baseline — before continuous batching

Honest starting numbers for the inference-server, captured the day the metrics +
benchmark harness landed. **These are intentionally the *before* picture.** They
document the current single-worker CPU architecture so Week 2 (continuous
batching + KV caching) has a concrete before/after to prove.

> Numbers are indicative, not a strict specification. They vary run-to-run
> because everything runs on the local CPU. Re-run `benchmarks/run.py` to
> reproduce.

## Environment

| Item | Value |
|------|-------|
| Backend | `inference-server` v0.1.0 (FastAPI + llama.cpp on CPU) |
| Chat model | Qwen2.5-0.5B-Instruct (`qwen2.5-0.5b-instruct-q4_k_m.gguf`, Q4_K_M) |
| Context | 512 tokens |
| Threads | 2 (`MODEL_THREADS=2`) |
| Scheduler workers | 2 |
| Protocol | OpenAI-compatible SSE streaming |
| Load driver | `benchmarks/run.py` (httpx2 async) |

## Streaming — single concurrent client

Measured with `benchmarks/run.py` (concurrency=1, 4 requests, `max_tokens=24`,
fixed short-story prompt).

| Metric | p50 | mean | max |
|--------|-----|------|-----|
| TTFT (time-to-first-token) | ~110–360 ms | ~630–840 ms | up to ~3 s |
| Inter-token latency (ITL) | ~58–132 ms | ~59–132 ms | ~154 ms |
| Total latency | ~1.0–3.4 s | ~1.6–3.4 s | ~4.7 s |
| Throughput | ~6–10 tokens/sec | | |

Observations:

- **First token is fast** (~100 ms) — prefill of a short prompt is cheap.
- **Token cadence is ~60–130 ms** — the dominant cost is 24 transformer layers ×
  decode step on 2 CPU threads.
- The wide total-latency spread comes from the scheduler queueing a test prompt
  that produces a longer completion (some requests hit the `max_tokens` cap).

## Streaming — under concurrency (the painful part)

| Concurrency | Requests | Result |
|-------------|----------|--------|
| 1 | 4 | Full success, metrics above |
| 2 | 2–4 | Streams stall: requests return 200 with **zero streamed tokens**, effectively degraded |
| 4 | 4 | **Connection errors** — server can't accept/hold more concurrent streams |

This is the headline finding: **the current server collapses beyond a single
concurrent stream.** The scheduler serializes generation on 2 CPU threads with a
per-request context, so concurrent SSE clients starve each other and the event
loop / connection handling loses capacity.

## Non-streaming chat (single live probe)

First-request cold numbers from a direct `/v1/chat/completions` call (small
`max_tokens`):

| Metric | Value |
|--------|-------|
| TTFT-equivalent (full generation) | ~2.2 s (cold first call) |
| Latency p50 (later calls) | ~10 ms after warm |
| Tokens recorded | prompt 7 / completion 3 |

Note: non-streaming requests have no TTFT/inter-token by definition; their
generation time is captured as total latency in `/metrics`.

## What this tells us (and what to do about it)

1. **Single-client streaming latency is fine** for small models on CPU.
2. **Concurrency is the killer.** The architecture must batch requests into one
   model call and share a KV cache across requests — precisely **Week 2's
   continuous-batching work**.
3. **Proof target:** after Week 2, re-run `benchmarks/run.py` and show
   concurrency=2/4 succeeding with TTFT and ITL that hold reasonably flat, and
   tokens/sec that **rises** with concurrency instead of collapsing.

Also observed (need a small follow-up): the `/v1/models` and non-streaming routes
already report `by_status` cleanly in `/metrics` (2xx/4xx/5xx), and the rate
limiter correctly rejects bursts with 429 (covered by unit tests) — both are
healthy and unaffected by the concurrency ceiling.

## How to reproduce

```bash
# terminal 1
cd inference-server
uv run uvicorn inference_server.main:app --port 8000

# terminal 2
uv run --project benchmarks python -m benchmarks.run   # defaults: 1,2,4,8 / 10 reqs
```
