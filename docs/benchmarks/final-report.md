# Final benchmark report — the whole month, consolidated

The closing document for Month 1. Every number below came from the repo's own
benchmark harness (`benchmarks/run.py`, `benchmarks/sweep.py`) against the real
model on this 4-core CPU box. Nothing is simulated, and the limits are named.

## Environment (same across all weeks)

| Item | Value |
|------|-------|
| Backend | `inference-server` v0.1.0 (FastAPI + llama.cpp on CPU) |
| Chat model | Qwen2.5-0.5B-Instruct (Q4_K_M default, Q8_0 sibling) |
| Context | 512 tokens · threads 2 · workers 2 |
| Protocol | OpenAI-compatible SSE streaming |
| Load driver | `benchmarks/` (httpx2 async) |

## The headline numbers

### Week 1 baseline — where we started

| Metric | Value |
|--------|-------|
| TTFT p50 (single stream) | ~110–360 ms |
| Inter-token latency (ITL) | ~58–132 ms |
| Throughput | ~6–10 tokens/sec |
| Concurrency 2 | streams return 200 with **zero streamed tokens** |
| Concurrency 4 | **connection errors** — box loses capacity |

The box collapsed past one stream. That is the honest starting point
(`docs/benchmarks/baseline.md`).

### Week 2 — admission control changed the failure mode

| Test | Result |
|------|--------|
| 8 concurrent, `MAX_IN_FLIGHT=2` | exactly **2 served (200), 6 cleanly rejected (503 + Retry-After)** |
| Box responsiveness during overload | health/metrics keep answering |

Not faster — **safer**. Overload went from "server unresponsive" to "bounded,
typed rejection" (`docs/benchmarks/batching-vs-baseline.md`).

### Week 3 — quantization + routing (measured)

| Axis | Q4_K_M | Q8_0 |
|------|-------:|-----:|
| GGUF on disk | 491.4 M | 675.7 M (+37%) |
| Router quality score | 0.55 | 0.9 |
| Measured ITL p50 | ~74–94 ms | ~79 ms |
| Measured tokens/s | ~10 | ~9.8 |
| Quality probe (2+2 ×10) | 100% | 100% |

Honest read: at 0.5B scale Q8 buys ~no measurable quality at +37% memory; the
router rightly defaults to Q4 unless a client demands quality
(`docs/benchmarks/quant-sweep.md`).

## What was built across the month (the delta)

| Week | Capability | Proof |
|------|-----------|-------|
| 1 | Metrics (`/metrics`: TTFT/ITL/latency p50–p99, status counts) + benchmark harness + baseline | `metrics.py`, `benchmarks/`, `docs/benchmarks/baseline.md` |
| 2 | Priority-queue scheduler + admission control | `scheduler/`, 8→2/6×503 live proof |
| 3 | Router (quality/latency/cost scoring, health cooldown, fallback) + quant sweep + pluggable engine | `router/`, `engines.py`, `docs/benchmarks/quant-sweep.md` |
| 4 | Failure modes hardened (timeouts, graceful shutdown, stream cleanup) + FDE whiteboard | `docs/notes/failure-modes.md`, `docs/evidence/fde-100m-tokens-day.md` |

## Quality gates

- **44 tests, all passing** — scheduler (priority/FIFO/batching/cancel), router
  engine + wiring, metrics, admission, rate limit, engines, failure modes.
- **Live-verified repeatedly**: `GET /models`, `GET /routes`, streaming chat
  with `X-Router-Selected` / `X-Router-Reason`, Q8 route auto-registration.
- **`uv sync --no-dev --frozen`** green from both repo root and
  `inference-server/` (the Nixpacks install step), including the new packages.

## The honest "why N× slower than vLLM"

~100× on raw decode. Three named causes:
1. **CPU vs GPU memory bandwidth** (hardware floor, not fixable in code)
2. **No continuous batching** — one stream per context; throughput *collapses*
   with concurrency instead of rising (the vLLM trick)
3. **Runtime API limit** — the high-level llama.cpp API manages a per-request
   KV cache with no multi-sequence path

Documented, not faked: `docs/evidence/slower-than-vllm.md`.

## The narrative in one paragraph

I built an OpenAI-compatible server that speaks the real wire format, then made
it a *system*: a bounded scheduler with admission control that survives
overload with typed 503s, metrics that measure TTFT/ITL/latency in real
percentiles, a router that picks the right backend per request and explains
why, a quantization sweep that produces the numbers behind the routing
decisions, and a pluggable engine seam so the next runtime drops in without
rewiring. The benchmark harness that produced every number in this report is
the same one an interviewer would run — and the box's honest limits (single
CPU worker, no continuous batching yet, ~100× slower than vLLM) are written
down with their causes and their fix paths.

## Reproduce everything

```bash
# tests
uv run pytest scheduler/tests -q            # 44 pass

# live server (from inference-server/)
uv run uvicorn inference_server.main:app --port 8000

# concurrency ramp
uv run --project benchmarks python -m benchmarks.run

# quantization sweep (Q4 vs Q8)
uv run --project benchmarks python -m benchmarks.sweep

# frozen build (the Nixpacks install step)
uv sync --no-dev --frozen
```
