# Roadmap — 4 weeks to "AI Systems / Inference Engineer" readiness

> Time-boxed one-month plan, derived from the Andrew Ng "AI Engineering Skills
> Map" and the OpenAI/OpenRouter/Modal FDE analysis. The whole point: **turn the
> existing OpenInference server from a demo into a system you can benchmark,
> optimize, and defend** — evidence that you operate at inference-engineer level,
> not "I can call an LLM API."
>
> Target profile: **AI Systems / Inference Engineer who can deploy and optimize
> production AI systems end-to-end.** The flagship artifact is your own
> OpenAI-compatible inference server, hardened and benchmarked.

How skills map to the work below:

| Andrew Ng skill | What you execute here |
|---|---|
| Building & deploying AI apps | The live server, streaming, tools, deployments |
| Software engineering fundamentals | Distributed-ish queue, batching, metrics, error handling |
| Using coding agents | You'll steer agents to implement the features; you verify with benchmarks + tests |
| Shaping the build | Each feature ends with a benchmark + written tradeoff, not just code |

---

## Week 1 — Metrics, observability & the benchmark harness

**Why first:** you cannot optimize what you cannot measure. Everything after
this week is validated against numbers.

- [ ] **M1. Metrics middleware** — a `metrics/` package in `inference-server`
      that records, per request: `TTFT`, `TPOT`, `ITL` (inter-token latency),
      total latency, prompt/completion tokens, and a request counter.
- [ ] **M2. Metrics endpoint** — expose cumulative + windowed stats (p50/p95/p99
      for latency) at `GET /metrics` (or a `/v1/metrics` behind auth).
- [ ] **M3. Benchmark harness** — a `benchmarks/` script that drives the server
      with a concurrency ramp (1, 2, 4, 8 users) and reports tokens/sec,
      throughput, TTFT/TPOT/ITL, p50/p95/p99, CPU & memory.
- [ ] **M4. Load test** chat (stream + non-stream) throttled by rate limiting —
      prove the limiter holds and note impact.
- [ ] **M5. Baseline report** — record the current numbers *in `docs/`* (before
      any optimization) so later weeks show wins. Test with real Qwen2.5-0.5B.

**Definition of done:** `GET /metrics` works; `benchmarks/run.sh` prints a
repeatable report; `docs/benchmarks/baseline.md` exists with honest numbers.

---

## Week 2 — Continuous batching & KV caching

**Why:** this is the single biggest throughput win and the heart of "inference
infrastructure" credibility.

- [ ] **B1. Request batching in the scheduler** — instead of one model context
      per worker, drain multiple queued jobs into one generate call (llama.cpp
      `n_batch`/batch API; inspect vLLM/SGLang for the pattern).
- [ ] **B2. Continuous batching semantics** — handle streams arriving/mid-stream:
      add/remove sequences while generation progresses, not just fixed batches.
- [ ] **B3. Prefix caching** — detect shared prompt prefixes across requests in
      a window and skip recomputation (carry the KV cache forward).
- [ ] **B4. Learn from `scratch-inference/kv_cache.py`** — read the from-scratch
      KV cache to internalize why prefill/decode differ O(seq) vs O(1) work.
- [ ] **B5. Re-baseline** — run Week-1 harness, compare tokens/sec vs baseline.
- [ ] **A1. Admission control** — optional first cut: reject/queue when
      `in_flight + queue_size` exceeds capacity (protects the box).

**Definition of done:** `benchmarks/` shows measurable throughput gain over
baseline; `docs/benchmarks/batching-vs-baseline.md` written.

---

## Week 3 — Router, quantization sweep & the "why" write-ups

**Why:** routing + quantization turn raw serving into *cost/latency engineering*,
which is the specific skill FDE/inference roles pay for.

- [ ] **R1. Routing engine** — a `router/` package that selects a model/backend
      per request driven by inputs (quality, latency budget, cost, context
      length, availability, health, history) with fallback + timeout + retry.
- [ ] **R2. Wire routing into chat router** — `request.model` can route across
      multiple served models/providers; log the routing decision + reason.
- [ ] **R3. Compression / quantization sweep** — serve the same model at Q4 vs
      Q8 (and note GGUF size/memory) and benchmark quality-latency-cost deltas.
- [ ] **Q1. Structured-evidence write-ups** — publish 2 of the planned posts in
      `docs/` or your blog: (1) "I built an OpenAI-compatible LLM server from
      scratch", (2) "Why my server was N× slower than vLLM" (use real numbers).
- [ ] **W1. Migration/portability** — make the model engine pluggable
      (llama.cpp / scratch) so the server isn't welded to one backend.

**Definition of done:** router can answer "given this workload, which
model/config and why"; quantization + routing benchmark notes in `docs/`.

---

## Week 4 — Reliability, deployability & the FDE story

**Why:** a capable system nobody can deploy or explain is worthless to a
customer. Finish with production hardening and a narrative.

- [ ] **D1. Single-binary-friendly / container build** — ensure Nixpacks build
      still works with the new packages (or add a Dockerfile).
- [ ] **D2. Failure modes** — graceful shutdown of in-flight jobs, timeout
      handling, backpressure behavior under overload, clear 503s.
- [ ] **P1. FDE simulator mini-report** — pick one persona (e.g. an app serving
      100M tokens/day at a p95 TTFT budget) and write the architecture + tradeoff
      analysis you'd whiteboard in an interview (from `ARCHITECTURE.md` §3).
- [ ] **B6. Final benchmark report** — consolidated numbers + the "why" narrative.
- [ ] **K1. Interview readiness** — you can now answer the whiteboard prompt in
      `ARCHITECTURE.md` §3 end-to-end with real measurements backing each claim.

**Definition of done:** a deployed, hardened server + a portfolio-grade write-up
that reads as "I optimize production inference systems."

---

## What is intentionally NOT in this month

Deliberately deferred so OpenInference ships in 4 weeks (you have other products
to build). These remain in the wider portfolio roadmap but are out of this
time-box:

- Full doc/intelligence platform (Project 4 of the ChatGPT plan)
- Building a production coding agent (Project 6)
- Full multi-provider evals suite (Project 3 beyond the basics needed above)
- Deep CUDA/kernel work (learn alongside, don't block shipping)

## Wider portfolio (post Month-1)
`inference-server` → `scheduler` → `kv-cache`/`tokenizer` (reference exists in
`scratch-inference/`) → `router` → `evals` → `distributed-serving` → `monitoring`.
See `todo.md` for the long-form ordered list.
