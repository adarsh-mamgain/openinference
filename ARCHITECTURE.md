# Architecture

This is the authoritative view of how the OpenInference workspace is put together
now, and where it is headed over the next month. It is the document referenced by
the `README.md` and `todo.md` from the repo root.

## 1. What we actually run today

The workspace is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
with three members. Only one of them is a deployable service:

```
openinference/
├── inference-server/   ← THE service you run (FastAPI + llama.cpp)
├── scheduler/          ← internal library (priority-queue request scheduler)
└── scratch-inference/  ← from-scratch numpy stack (learning / reference only)
```

### Current execution path (chat + streaming)

```
Client (any OpenAI SDK)
   │
   ▼
FastAPI  ├─ /health            (probe)
         ├─ /                  (landing page)
         ├─ /v1/chat/completions   ──┐
         ├─ /v1/embeddings          │  routed through...
         ├─ /v1/models              │
         │                           ▼
         │                    Scheduler (priority queue)
         │                    └─ Worker pool (asyncio, bounded)
         │                           │  runs real local Qwen2.5-0.5B
         │                           ▼
         │                    llama.cpp (CPU) ← GGUF weights
         │                           │
         ▼                           ▼
   OpenAI-compatible JSON / SSE stream
```

Both streaming and non-streaming chat flow through the internal scheduler. The
scheduler is not an HTTP service — the FastAPI router is the *only* API surface.

### What is already built (verified)

| Concern | Where | Notes |
|---------|-------|-------|
| OpenAI wire format | `inference-server/src/inference_server/schemas.py` | request/response Pydantic models matching OpenAI |
| Chat completions | `routers/chat.py` | non-streaming + SSE streaming |
| Embeddings | `routers/embeddings.py` | real local embedding model |
| Model list | `routers/models.py` | `GET /v1/models` |
| Tokenizer (real) | `llm.py` | token counts from the actual tokenizer |
| Tool / function calling | `tools.py`, `scheduler/scheduler.py` | model-driven loop, bounded turns |
| Auth | `auth.py` | Bearer API key |
| Rate limiting | `rate_limit.py` | fixed-window, in memory |
| Priority scheduling | `scheduler/` | heap + FIFO tie-break, cancel, backpressure |
| Streaming bus | `scheduler/events.py` | in-process pub/sub for SSE deltas |
| Deployment | `nixpacks.toml` | Coolify/Nixpacks, CPU-only |
| From-scratch reference | `scratch-inference/` | BPE tokenizer, KV cache, transformer in numpy |

## 2. Known limitations today (why the target architecture exists)

1. **No continuous batching** — each worker holds one model context at a time
   and processes one request. Throughput is a fraction of what vLLM/SGLang get.
2. **KV cache is per-request and not paged** — memory is allocated for the full
   context window even when a request only uses a few tokens.
3. **No metrics/observability** — nothing exports latency (TTFT/TPOT/ITL),
   throughput, GPU/CPU utilization, or cost per request.
4. **No prefix caching or routing** — every request recomputes shared prefixes,
   and there is no multi-model / multi-provider routing layer.
5. **Single-node, CPU-only, single model** — no tensor/pipeline parallelism, no
   quantization sweep, no admission control, no autoscaling.

## 3. Target architecture (the end-state we're building toward)

This is the shape of a "miniature OpenRouter + vLLM", the north-star project.
Highlighted components are **already built**; the rest are the month's plan.

```
                         Clients  (OpenAI SDK / curl)
                           │
                           ▼
                    ┌───────────────┐
                    │  Global API   │   FastAPI (exists)
                    │  Gateway      │   auth · rate-limit · middleware
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   Router      │   *** NEW — multi-model/provider
                    │   Engine      │   latency-aware, cost-aware, fallback
                    └───────┬───────┘
                            │
                  ┌─────────┴──────────┐
                  ▼                     ▼
        ┌───────────────┐      ┌───────────────┐
        │ Model /       │      │  Cached /     │   *** prefix cache
        │ Provider A    │      │  fallback     │
        └───────┬───────┘      └───────────────┘
                │
                ▼
        ┌───────────────┐
        │   Scheduler   │   priority queue (exists)
        └───────┬───────┘
                ▼
        ┌───────────────┐
        │ Continuous    │   *** NEW — iterative batching across requests
        │ Batching      │
        └───────┬───────┘
                ▼
        ┌───────────────┐
        │   KV Cache    │   *** NEW — paged / prefix-aware allocation
        │  (paged)      │
        └───────┬───────┘
                ▼
        ┌───────────────┐
        │ Model Engine  │   llama.cpp today → pluggable (scratch, vLLM)
        └───────┬───────┘
                ▼
               GPU / CPU
                │
                ▼
        ┌───────────────┐
        │   Metrics /   │   *** NEW — TTFT, TPOT, ITL, throughput, cost
        │   Evals       │
        └───────┬───────┘
                ▼
        Cost / Latency / Quality dashboard
```

## 4. Month-lookahead: what gets added where

| New capability | Primary home | Depends on |
|----------------|--------------|------------|
| Continuous batching | `inference-server` batching module | scheduler |
| Paged / prefix KV cache | `inference-server` cache module | (scratch KV cache as reference) |
| Metrics (TTFT/TPOT/ITL/etc.) | new `metrics/` package | — |
| Benchmark harness vs vLLM/llama.cpp | `benchmarks/` | metrics |
| Router engine | new `router/` package | models endpoint |
| Admission control / scheduling policies | `scheduler/` | scheduler |
| Evals + error analysis | new `evals/` package | models |

See `todo.md` for the ordered, week-by-week tasks.

## 5. Repo layout conventions

- **`inference-server/`** — the deployable service. Owns HTTP, config, auth,
  rate limiting, landing page, and now the model-serving internals (batching,
  cache, metrics).
- **`scheduler/`** — a library consumed by `inference-server`. No HTTP surface.
- **`scratch-inference/`** — an educational from-scratch stack. **Not deployed.**
  Kept as the reference for KV-cache and tokenizer learning and as a candidate
  pluggable runtime.
- Anything new that is a *service* or *library* and needed by the product should
  live in the workspace and be wired the same way `scheduler` is: a package
  imported by `inference-server`, not a separate HTTP process (unless the month
  plan explicitly calls for a standalone service like the router).
