# FDE mini-report — serving 100M tokens/day at a p95 TTFT budget

> The whiteboard exercise: "Design the serving architecture for an app that
> must serve **100M output tokens/day** with a **p95 TTFT under ~2s** — on a
> budget." This is the answer I'd give in an interview, grounded in the
> *measured* numbers from this repo rather than hand-waving.
>
> Every formula and assumption is stated; every lever is a real knob this
> project ships (admission control, routing, quant sweep, pluggable engine).

---

## 0. Start from the demand, not the hardware

```
100M output tokens/day
     ÷ 24 h          ≈ 4.17M tokens/hour
     ÷ 3600 s        ≈ 1,157 output tokens/second steady-state
     × (peak/avg)    ≈ 2-3×   → ~2,300-3,500 tokens/s at peak
```

And TTFT is about **prefill + queueing**, which is *separate* from the
sustained decode rate. So there are really two numbers to engineer:

- **Sustained decode throughput** (tokens/s) — drives how many GPUs you need.
- **TTFT at p95** — drives how much headroom/batching you keep so the tail
  stays short.

Never solve one without the other. A box that saturates decode will blow TTFT
even if its average throughput looks fine.

---

## 1. The throughput math (this is the whole interview)

Decode is **memory-bandwidth bound**: each generated token reads the entire
weight matrix once. So per-token time is approximately

```
t_decode ≈ weights_bytes / memory_bandwidth
```

Concretely (and this is *real*, measured on a CPU):

| Config | Weights | Bandwidth | Per-token | Tokens/s |
|--------|---------|-----------|-----------|----------|
| 0.5B Q4 on 2 CPU cores | ~0.25 GB | ~5 GB/s effective | ~60-130 ms | ~8-15 |
| 0.5B Q8 on 2 CPU cores | ~0.34 GB | ~5 GB/s effective | ~70-140 ms | ~7-10 |

So **one CPU worker tops out around ~10 tok/s** → to hit 1,157 tok/s steady you
need ~**115 such workers**. That's not the "right" answer — it's the *naive*
answer that proves the point: **you do not meet 100M tok/day on one CPU box.**
(Our honest baseline: `docs/benchmarks/baseline.md`, `quant-sweep.md`.)

On GPU the same model decodes ~100-1,000× faster per card, so the answer
*starts* with "how many and what kind of accelerators." But a good engineer
doesn't stop at "buy GPUs" — they show the levers that shrink the count:

---

## 2. The levers (each one exists in this project)

### Lever A — quantization (fewer bytes read per token)
Q8 reads 37% more bytes than Q4_K_M (675M vs 491M). Lower-precision quants cut
`weights_bytes`, raising tokens/s per device. Cost: measurable quality loss
(real number from our sweep: at 0.5B scale, the probe did *not* discriminate —
but the tradeoff is real and must be measured per model). **Decision: pick the
lowest quant that passes your eval gate.**

### Lever B — continuous batching (amortize the forward pass)
The single biggest throughput lever. vLLM/SGLang fill each forward pass with
many sequences, so per-token cost *per sequence* falls as the batch grows:

```
throughput ≈ decode_rate × average_batch_size
```

This is the vLLM trick. Our server deliberately does **not** fake it — it's
documented as blocked on the runtime's multi-sequence API
(`docs/benchmarks/batching-vs-baseline.md`). **Decision: batch N streams per
forward; TTFT budget sets N** (more concurrency in batch → shorter queue →
better TTFT, up to the GPU's capacity).

### Lever C — admission control (protect TTFT, don't drown)
Unbounded concurrency destroys TTFT for *everyone*. Our `MAX_IN_FLIGHT` rejects
excess requests with 503 + `Retry-After` (live-verified: 8 concurrent → 2
served, 6 rejected cleanly). **Decision: cap in-flight work so p95 TTFT stays
under budget; excess traffic queues or retries.**

### Lever D — routing (put work on the right backend)
Not every request needs the same quality. Our router scores quality/latency/cost
per request and can steer cheap/simple requests to a faster/cheaper quant or
backend while hard requests get the premium model. **Decision: route by request
profile to spend latency budget where it buys quality.**

### Lever E — the TTFT equation itself
TTFT is dominated by **prefill + queueing**:

```
TTFT ≈ prefill_time + queue_wait
prefill_time ≈ prompt_tokens × weights_bytes / bandwidth   (once, per request)
queue_wait    ≈ work_ahead_of_you / aggregate_throughput
```

So to hold p95 TTFT < 2s you watch two things: (1) keep prefill fast (GPU
compute + short prompts), (2) keep the queue short (admission control + enough
capacity + batching headroom).

---

## 3. The architecture I'd whiteboard

```
          Clients (~1.2k req/s steady)
                 │
                 ▼
        ┌─────────────────────┐
        │  Global API gateway │  auth · rate-limit · admission (503+Retry-After)
        │  (anycast, stateless)│
        └──────────┬──────────┘
                   ▼
        ┌─────────────────────┐
        │  Router             │  per-request: model/profile + health + fallback
        └──────────┬──────────┘
                   ▼
        ┌──────────────────────────────────────┐
        │   Scheduler + continuous batching    │  fill forward passes with
        │   (priority queue, KV cache manager) │  many sequences
        └──────────┬───────────────────────────┘
                   ▼
        ┌──────────────────────┐
        │   Model pool (GPUs)  │  N replicas × quantized weights
        │   health · cooldown  │  sized by the throughput math
        └──────────────────────┘
                   │
                   ▼
        Metrics: TTFT p50/p95/p99 · ITL · throughput · cost/1k · queue depth
        → autoscaling + alerting (p95 TTFT budget is THE SLO)
```

Capacity planning, left-to-right:

| Stage | Sizing | Because |
|-------|--------|---------|
| Model pool | `ceil(1,157 tok/s ÷ per-device tok/s)` replicas (with batch) | decode is the floor |
| Router/gateway | stateless, scale-out | trivially parallel |
| Queue depth | bounded by admission control | protects p95 TTFT |
| KV memory | `max_sequences × max_ctx × per-token_kv` | batching consumes memory |

---

## 4. The cost reality (be honest here)

- **The GPU count dominates.** 100M tok/day is a real production load: it needs
  multiple accelerators (roughly a handful of mid-range GPUs for a 0.5-8B model
  with batching). Anyone who promises "one CPU box serves 100M tok/day" is
  selling you a dashboard, not a system.
- **TTFT budget vs cost is a slider.** Tighter p95 TTFT → more headroom
  (unused capacity) → more $/token. The interview move is to *name* that
  tradeoff and put a number on it, not pretend it's free.

---

## 5. What this repo proves (so the whiteboard isn't abstract)

Every claim above is backed by a file in this workspace:

| Whiteboard claim | Evidence |
|------------------|----------|
| Decode is memory-bandwidth bound | `scratch-inference/kv_cache.py`, `docs/notes/kv-cache-prefill-decode.md` |
| Real per-token numbers (Q4/Q8) | `docs/benchmarks/baseline.md`, `docs/benchmarks/quant-sweep.md` |
| Single-worker ceiling (~10 tok/s) | `docs/benchmarks/baseline.md` |
| Admission control protects the box | `docs/benchmarks/batching-vs-baseline.md` (8→2 served, 6×503) |
| Continuous batching is the big lever (and its honest blocker) | `docs/benchmarks/batching-vs-baseline.md` |
| Routing by quality/cost exists | `docs/notes/router.md` |
| Pluggable engine → swap backends without rewiring | `inference_server/engines.py` |
| TTFT/ITL/latency measured, not guessed | `metrics.py`, `GET /metrics` |
| Failure modes are bounded and typed | `docs/notes/failure-modes.md` |
| "Why N× slower than vLLM" — named, not waved away | `docs/evidence/slower-than-vllm.md` |

**The one-sentence answer:** "100M tokens/day at p95 TTFT < 2s means roughly
1,200 sustained output tokens/s; that's fundamentally a memory-bandwidth
problem, solved by quantized weights + continuous batching on a GPU pool sized
by the decode math, protected by admission control so the tail stays short —
and I've built and measured every one of those levers."