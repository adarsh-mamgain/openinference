# OpenInference explainer — everything we built, with diagrams

A from-the-ground-up explanation of the inference server, the scheduler, the
router, the metrics, and the evidence. Read top-to-bottom; each section's
concepts build on the ones before it.

---

## 1. The one-paragraph story

We built an **OpenAI-compatible inference server** (a FastAPI app that speaks
`/v1/chat/completions`, `/v1/embeddings`, etc.) that runs a real
**Qwen2.5-0.5B-Instruct** model on CPU via llama.cpp. Then we made it *look like
a production system*: requests go through a **priority-queue scheduler** with
**admission control** (so overload fails fast instead of killing the box), every
request is **observed** (TTFT, ITL, latency — recorded and available at
`/metrics`), a **router** picks which of several served models answers each
request and explains why, and a **benchmark harness** proves every number we
claim. The final evidence write-ups are in `docs/evidence/`.

The point is not "I wrote an LLM API" — it's **"I can measure it, load it,
optimize it, and defend the tradeoffs in an interview."**

---

## 2. The big picture — where each piece lives

```
                        ┌──────────────────────────────────────────────┐
                        │              inference-server                │
   HTTP client          │                                              │
 ────────────► ┌─────┐  │  ┌─────────┐   ┌──────────────┐   ┌─────────┐ │
               │Auth │──►│ RateLimit │──►│  /v1/chat/    │──►│ Router  │ │
   (OpenAI     └─────┘   └─────────┘   │  completions   │   └─────────┘ │
    compat)                             └──────────────┘     │ select   │
                                                              │ route +  │
                                                              │ hints    │
                                                              ▼          │
                                        ┌─────────────────────────────┐  │
                                        │         Scheduler           │  │
                                        │  ┌───────────────────────┐  │  │
                                        │  │ PriorityQueue (bounded)│  │  │
                                        │  └───────────┬───────────┘  │  │
                                        │              ▼              │  │
                                        │   Worker 0   Worker 1       │  │
                                        │        \       /            │  │
                                        │     ┌─────┴─────┐           │  │
                                        └────►│  Model     │           │  │
                                              │ (llama.cpp)│           │  │
                                              └─────┬─────┘           │  │
                                                    ▼ (output)         │  │
                                        + metrics.py observes EVERYTHING│  │
                                        + GET /metrics, GET /health    │  │
                        └──────────────────────────────────────────────┘  │
```

Three layers are worth teasing apart, because they map directly to interview
concepts:

| Layer | What it is | The production name for it |
|-------|-----------|---------------------------|
| HTTP + auth + rate limit | FastAPI routes, `Depends(require_api_key)` | "the control plane / gateway" |
| Scheduler + admission control | priority queue + worker pool + capacity check | "the data plane / batching" |
| Router (Week 3) | which model serves this request, and why | "the routing / gateway layer" |
| Metrics (Week 1) | TTFT / ITL / latency / tokens | "observability" |
| Benchmarks (`benchmarks/`) | concurrency ramp + quant sweep | "load testing / regression insurance" |

When an interviewer says "walk me through a request," you trace that yellow
path: **auth → rate-limit → router → scheduler → worker → model → SSE back out**,
with metrics recorded along the way.

---

## 3. The request lifecycle — end to end

```
Client
  │  POST /v1/chat/completions
  │  {messages, max_tokens, stream:false, model:"qwen..."}
  ▼
┌──────────────────────────  middleware: observe_requests  ──────────────┐
│  start = monotonic() ; (latency recorded when the response returns)     │
└──────────────────────────────────────────────────────────────────────────┘
  ▼
[1] require_api_key      — Bearer token vs settings.api_key
[2] rate_limit           — fixed-window counter: >100/min → 429
  ▼
[3] router.route(...)    — pick a Route (q4 default, or q8 sibling, or...)
      "explicit request ... and route is healthy"        (X-Router-Reason)
      run = "auto" / hints from X-Router-* headers                 ▼
[4] scheduler.submit_chat(..., model_name=<route id>)
      ├─ Admission check: in_flight + queued < max_in_flight ?
      │     NO  → 503 + Retry-After: 2       (server refuses, box survives)
      │     YES → Job enqueued onto PriorityQueue (priority-then-FIFO)
      ▼
[5] idle Worker pops the job
      └─ _execute(job):
           ├─ NON-streaming: asyncio.to_thread(exec_model.generate(...))
           │                    → model-driven tool-calling loop
           └─ streaming:       exec_model.stream(...) yields token deltas
                                 → bus.publish(job_id, delta)
  ▼
[6] HTTP layer reassembles:
      non-streaming → one json response {choices:[...], usage:{...}},
      streaming     → SSE frames: role chunk · token chunks · done · [DONE]
  ▼
Client sees OpenAI-compatible output. /metrics was fed TTFT, ITL, latency,
token counts the whole way.
```

**Key mental model:** the HTTP layer is *fast and thin*; the *model* runs on
worker threads off the event loop (via `asyncio.to_thread`), so the event loop
stays free to serve health/metrics/other requests while a stream generates.

---

## 4. The scheduler — a priority queue with a backpressure brake

A production LLM server must **never** let unbounded concurrency reach the
model. The scheduler sits between HTTP and the model and enforces that.

```
                      submit_chat()
                            │
                            ▼
              ┌─────────────────────────────┐
              │   can_admit()?              │
              │   in_flight + queued        │
              │        <  max_in_flight     │
              └─────────┬─────────┬─────────┘
                     NO  │        │ YES
                         ▼        ▼
                  raise 503   enqueue QueueItem
                 (Retry-     (priority, seq, job_id)
                  After)           │
                                   ▼
                        ┌───────────────────┐
                        │   PriorityQueue   │   bounded (maxsize)
                        └───────────────────┘
                                   ▼
                   ┌───────────────┴───────────────┐
                   ▼                               ▼
              Worker 0                          Worker 1
              ─────────                          ─────────
              pops job, RUNNING,                 pops job, RUNNING,
              in_flight += 1                     in_flight += 1
              runs the model                     runs the model
              COMPLETED / FAILED                 COMPLETED / FAILED
              in_flight -= 1                     in_flight -= 1
```

The two tuning knobs that matter for interviews:

- **`max_in_flight`** — how much work the box is willing to be "committed" to
  (in flight + queued). Above it, requests are rejected *instead of allowed to
  starve or kill the machine*. This is the same idea as vLLM's
  `--max-num-seqs` and `--max-num-batched-tokens`. Our live proof:
  **8 concurrent → 2 served, 6 rejected with a clean 503**, and the box stayed
  responsive (`docs/benchmarks/batching-vs-baseline.md`).
- **`num_workers`** — how many generation jobs run at once (2 on our CPU box).
  Because each job holds its own model context up in memory, this is also a
  memory knob.

The subtle wins that are easy to miss but impressive to know:

- Workers loop `for item in await queue.get()` forever — this is a classic
  **single-consumer-per-worker** pattern; the queue itself handles ordering.
- `asyncio.to_thread` keeps the *model's blocking* loops off the event loop so
  the loop can still answer `/health` mid-generation.
- `subscribe_stream` in the router reads the job's stream queue, so the HTTP
  layer and the worker are decoupled by a message bus, not by a locked buffer.

---

## 5. Metrics — what TTFT, ITL, and latency actually mean

This is the section that makes engineering sense. All three derive from a
streaming timeline:

```
request              ┌ first token       ┌ token 2      ...  ┌ last   ┌ stream
dispatched at T0     │ arrived at T1     │ at T2            │ at Tn   │ done
     │               │                   │                  │         │
     ▼               ▼                   ▼                  ▼         ▼
─────●───────────────●───────●───────────●──────○──────○──────●─────────●
     |<── TTFT ─────>|                                       time
               |<- ITL ->|<- ITL ->|
                               |<──────── total latency ────────────>|
```

| Metric | Definition | What it reveals | Why it matters |
|--------|-----------|-----------------|----------------|
| **TTFT** (time-to-first-token) | dispatch → first content delta | prompt **prefill** cost + queueing + scheduling | Users perceive "is it working?" from the first token. Bad TTFT = slow prefill or long queue. |
| **ITL** (inter-token latency) | gap between consecutive deltas | **decode** speed (per-token) | Steady ITL = stable cadence; climbing ITL = saturation/slowdown mid-stream. |
| **Total latency** | end-to-end | everything | End-to-end user experience, aggregates the above. |
| **p50 / p95 / p99** | percentile over the window | *distribution*, not just average | p99 is what catches tail latency — the metric SLOs are written in |

Our metric `summary()` keeps a *sliding window* of each sample list and can
emit min / p50 / p95 / p99 / max / mean, plus `requests.by_status`
(2xx/4xx/5xx) and token totals — exactly what you'd wire into Prometheus in
production.

**The theory that underlies TTFT vs ITL (and why decode dominates):**
generation has two phases with very different costs:

- **Prefill** (process the prompt): work ∝ **prompt length × model size**
  — a short prompt is cheap, hence TTFT ~100–360 ms on our box.
- **Decode** (generate each next token): work ∝ **model size** per token —
  decoding 150 tokens is ~150 one-token passes. That's why ITL (~60–130 ms)
  dominates and why total latency scales with completion length.

Reference implementation and deeper notes:
`scratch-inference/kv_cache.py`, `docs/notes/kv-cache-prefill-decode.md`.

---

## 6. The router — which model serves this request, and why

Week 3's contribution. We don't just serve one model: the same Qwen model
exists as **two GGUF files at different quantizations** (Q4_K_M vs Q8_0), and a
0.5B model isn't the only possible backend — a `Route` can point at any local
GGUF *or* a provider endpoint. The router picks per request.

### Routes & the registry

```
registry.build_routes()
  default route   → qwen2.5-0.5b-instruct       (the Q4_K_M GGUF)
  sibling scan    → qwen2.5-0.5b-instruct-q8_0  (the Q8_0 GGUF auto-found)
       no new code — quantized siblings matching `-qN...gguf` auto-register

Route {
  id, backend(LOCAL|PROVIDER), model_path,
  quality     0..1       e.g. q4=0.55,  q8=0.9
  cost_per_1k_tokens     $/1k  (providers)
  latency_ms             estimate (faster routes score higher)
  enabled, available()
}
```

### Decision flow — explainable, not a black box

```
request.model? ─── yes ─► exact match, healthy? ── yes ─► win (reason:
   (explicit)                     │                          "explicit request...")
                          no (on cooldown)▼
   ── no / no match ─►  score all ELIGIBLE routes
                        eligible = enabled ∧ available ∧ not on cooldown
                           │
        score(route) = (w_q·quality + w_l·latency + w_c·cost) / (w_q+w_l+w_c)
                           │   w_q = 0.5 + 0.5·hints.quality
                           │   w_l = 0.5 + 0.5·(budget set?)
                           │   w_c = 0.5 + 2.0·hints.cost_sensitivity
                           ▼
                      top scorer wins
                      reason += ", scored best at 0.832 (q0.90; est 1800ms...)"
                      fallback_order = other routes best-first
```

Hints come from headers so the OpenAI-compatible wire format never changes:

```
X-Router-Quality: 0.9            → want max quality  → picks Q8
X-Router-Latency-Budget-Ms: 800  → want fast         → rejects slow routes
X-Router-Cost-Sensitivity: 1.0   → want cheapest     → picks Q4
```

### Health & cooldown — the self-healing part

```
RouteHealth keeps a sliding window of outcomes per route (last 100).

record(route_id, ok):
   ok      → clear cooldown
   !ok     → if error_rate >= 0.5  → cooldown_until = now + 30s

healthy(id) = not in_cooldown and error_rate < 0.5

The router therefore STOPS sending work to a route that's failing,
and retries failed requests on the next healthy fallback.
```

Then in `chat.py`: a failing primary route → `report_outcome(ok=False)` →
`next_fallback` → retry on the next healthy route, bounded by
`router_max_fallbacks`. Streaming cancels (client disconnects) are explicitly
**not** counted as backend failures — so a flaky client can't poison a route's
health score.

### Wiring summary (how it all connects)

```
chat.py on boot:
  router_engine = Router(build_routes(available_check=lambda: model.available))
  for non-default local route:
      scheduler.register_model(route.id, get_route_model(route.model_path))
                                                │
   ... so a routed job with model=route.id      ▼
   is executed by a REAL model instance bound   Scheduler._resolve_model(id)
   to that id, not just labeled.                └→ registry → actual model
```

---

## 7. Quantization sweep — what Q4 vs Q8 actually costs

The router makes decisions based on `quality`, `latency`, and `cost`. The sweep
(`benchmarks/src/benchmarks/sweep.py`) produces the *evidence* that backs those
decisions for a real model. Same model, two precision levels:

| Axes | Q4_K_M (default) | Q8_0 (sibling) |
|------|-----------------:|---------------:|
| GGUF on disk | 491.4 M | 675.7 M (+37%) |
| Router `quality` | 0.55 | 0.9 |
| Router est. `latency_ms` | 1000 | 1800 |
| Measured ITL p50 (live) | ~74–94 ms | ~79 ms |
| Measured tokens/sec (live) | ~10 | ~9.8 |
| Quality probe (2+2 ×10) | 100% | 100% |

**Read the result honestly:**

- Q8 costs **+37% memory** for a *small* CPU latency penalty — you pay real,
  measurable memory for fractional quality at 0.5B scale.
- The quality probe (factual answer) passes both — at this model size the probe
  **does not discriminate**, which we say outright rather than faking a delta.
- So on this box the router *correctly* defaults to Q4 unless the client
  explicitly asks for quality — that's the cost/latency engineering story.

---

## 8. The honest performance picture (and the vLLM comparison)

Number one thing to internalize: **this is a CPU single-worker box**, and the
benchmark harness proved exactly what that means.

| Concurrency | Baseline result (Week 1) |
|------------|--------------------------|
| 1 | healthy (TTFT ~110–360 ms, ITL ~58–132 ms, ~6–10 tok/s) |
| 2 | streams return 200 with **zero streamed tokens** |
| 4 | **connection errors** — the box loses capacity |

Then **admission control** changed the failure *mode*: 8 concurrent → 2 served,
6 clean 503s, box stays responsive. Faster? No — *safer*. Speed at concurrency
needs **multi-sequence decode** (continuous batching, the vLLM/SGLang core
trick), which our high-level llama.cpp API doesn't expose (it manages a
per-request KV cache). That's documented as a real, named block — 
`docs/benchmarks/batching-vs-baseline.md`, `docs/notes/kv-cache-prefill-decode.md`.

The write-up `docs/evidence/slower-than-vllm.md` gives the honest answer to
"why N× slower?": ~100× on raw decode (CPU bandwidth), plus a *different in
kind* collapse under concurrency (no batching), plus the runtime API limit —
three named, measured causes that make the box look intentional, not broken.

---

## 8b. Pluggable engine — the seam where a real runtime drops in

The server doesn't import llama.cpp (or numpy) anywhere in its HTTP/scheduler
layers. Everything talks to a `ModelEngine` interface
(`inference_server/engines.py`):

```
                      ModelEngine (ABC)
                      ─────────────────
   available        count_tokens(text)
   count_tokens_messages(messages)
   generate(messages, max_tokens, tools) -> (content, tool_calls, finish)
   stream(messages, max_tokens, tools)  -> Iterator[str]

        ┌───────────────────────────┐        ┌────────────────────────────┐
        │ LocalModel (llama.cpp)    │        │ ScratchEngine (numpy)      │
        │ GGUF, real streaming,     │        │ from-scratch stack,         │
        │ tool calling, tokenizer   │        │ no tools, single-delta      │
        └───────────────────────────┘        │ stream (reference impl)     │
                                            └────────────────────────────┘

   settings.model_backend = "local" | "scratch"   ← build_model_engine()
```

The scratch backend is the *same* code path as llama.cpp from the scheduler's
point of view — which is exactly the point: when a batch-capable runtime
arrives, it implements `ModelEngine` and `MODEL_BACKEND=that_runtime` flips the
whole server onto it. The `PROVIDER` route type (remote OpenAI-compatible
endpoint) is defined in the router model but not yet wired; it will be another
`ModelEngine` implementation.

---

## 9. Concept → file map (study list)

| Concept | Read |
|---------|------|
| Request lifecycle | `inference-server/src/inference_server/routers/chat.py` |
| Scheduler + admission | `scheduler/src/scheduler/scheduler.py` |
| Stream bus / events | `scheduler/src/scheduler/events.py`, `queue.py` |
| Metrics + percentiles | `inference-server/src/inference_server/metrics.py` |
| Routing engine + scoring | `inference-server/src/inference_server/router/engine.py` |
| Health + cooldown | `inference-server/src/inference_server/router/health.py` |
| Route registry + quant map | `inference-server/src/inference_server/router/registry.py` |
| Model wrapper (llama.cpp) | `inference-server/src/inference_server/llm.py` |
| Pluggable engine | `inference-server/src/inference_server/engines.py`, `llm.py::build_model_engine` |
| Failure modes | `scheduler/src/scheduler/scheduler.py` (timeout/grace), `docs/notes/failure-modes.md` |
| Config knobs | `inference-server/src/inference_server/config.py`, `scheduler/src/scheduler/config.py` |
| KV / prefill-decode theory | `docs/notes/kv-cache-prefill-decode.md`, `scratch-inference/kv_cache.py` |
| Baseline numbers | `docs/benchmarks/baseline.md` |
| Week-2 admission proof | `docs/benchmarks/batching-vs-baseline.md` |
| Router design | `docs/notes/router.md` |
| Quant sweep | `docs/benchmarks/quant-sweep.md`, `benchmarks/src/benchmarks/sweep.py` |
| Evidence write-ups | `docs/evidence/server-from-scratch.md`, `docs/evidence/slower-than-vllm.md` |
| FDE whiteboard | `docs/evidence/fde-100m-tokens-day.md` |
| Final report | `docs/benchmarks/final-report.md` |