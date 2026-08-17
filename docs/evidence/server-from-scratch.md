# "I built an OpenAI-compatible LLM server" — what actually went in

> Written for the AI Systems / Inference Engineer portfolio. This is the
> retroactive "why and how" behind the repo, with the real decisions and the
> real number that proves the architecture — not a tech-marquee list.

## The premise

Anyone can `pip install` a wrapper and stand up `/v1/chat/completions`. The bar
that separates "demo" from "system" is whether you can **measure, load, and
defend the thing under real conditions**. So I built an OpenAI-compatible
inference server with three non-negotiable properties:

1. The wire API actually is OpenAI-shaped (chat, streaming SSE, embeddings,
   tools, auth, rate limits) — clients don't know or care it's mine.
2. Every performance claim is a *measured* claim, produced by a benchmark
   harness in the repo.
3. The parts people put "Add in production: …" are the parts that exist in the
   code, not the parts on a slide.

## What's actually in it

```
inference-server/src/inference_server/
  main.py        FastAPI app, auth, rate limiting, /metrics
  routers/       chat (stream+tools), embeddings, models, routes
  scheduler/     priority queue + memory-bound exec model
  metrics.py     TTFT / ITL / latency / tokens, p50–p99
  router/        cost/latency/quality-aware routing + fallback + health
  llm.py         llama.cpp (gguf) model wrapper
```

Decisions worth explaining in an interview:

- **Scheduling is explicit, not incidental.** Requests land in a bounded
  priority queue; a fixed pool of workers executes them against a per-request
  model context. This is the seam where continuous batching, admission control,
  and routing all hang. `MAX_IN_FLIGHT` bounds how deep the overload can get.
- **SSE is read as raw frames, not line-decoded.** The benchmark client reads
  the chunked body until the terminal `[DONE]` frame so a slow stream doesn't
  invert the numbers — measuring TTFT/ITL correctly *is* part of the system.
- **Routing is a first-class object.** Every request yields a `RoutingDecision`
  with a reason string; the chosen route is executed by the scheduler, so
  "different route" is a *different backend*, not a label.
- **Metrics are windowed and cumulative.** p50/p95/p99 are computed over a
  sliding window so `/metrics` is useful mid-run, not just after.

## The number that matters

Single-client streaming on Qwen2.5-0.5B (CPU, 2 threads):

| Metric | Measured |
|--------|----------|
| TTFT (time-to-first-token) p50 | ~110–360 ms |
| Inter-token latency (ITL) | ~58–132 ms |
| Throughput | ~6–10 tokens/sec |
| End-to-end latency | ~1.0–3.4 s |

Stable, sane, and *honest* — but the headline is what the harness revealed
under concurrency:

| Concurrency | Reality |
|-------------|---------|
| 1 | healthy |
| 2 | streams return 200 with **zero tokens** |
| 4 | **connection errors** — server loses capacity entirely |

The single-threaded decode model cannot serve concurrent streams. That's the
honest "before" picture, in `docs/benchmarks/baseline.md`. It's what the next
weeks optimize against.

## What the follow-on weeks proved

- **Admission control** changed overload from "server unresponsive" to "clean
  bounded 503 + Retry-After": 8 concurrent → exactly 2 served, 6 rejected,
  health/metrics still answer. (Week 2, `docs/benchmarks/batching-vs-baseline.md`)
- **Routing + quantization sweep** turned raw serving into cost/latency
  engineering: the same 0.5B model at Q8_0 costs +37% disk for a small CPU
  latency penalty, and the router decides per request via quality/latency/cost
  weights + health-fed fallback. (Week 3, `docs/notes/router.md`,
  `docs/benchmarks/quant-sweep.md`)

## What's deliberately not in it (yet)

- Token-level continuous batching and prefix caching are **not** faked. They
  need a runtime that exposes multi-sequence decode (the high-level llama.cpp
  API manages a per-request KV cache we can't extend), so they're documented as
  blocked on that switch rather than implemented as a pretend batch layer.
- A GPU, an autoscaler, a fleet: this box is one CPU worker. The architecture
  (scheduler → exec model → router) is the production-sized shape; the capacity
  is not.

## Why this is evidence

The repo reads like the system an inference engineer builds: **bounded
scheduler, explicit admission control, routing with fallback, `/metrics` with
real percentiles, and a benchmark harness that produced every number above**.
Every claim is pointed at a file, and every file is either measured or its
limitation is named. That's the difference between a screenshot and a system.