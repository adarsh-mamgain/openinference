# OpenInference — Task List

The live, ordered task list. **Architecture**: see `ARCHITECTURE.md`.
**The 4-week plan with rationale**: see `ROADMAP.md`.

Legend: `[x]` done · `[ ]` next · `[-]` deferred past the month

---

## Month 1 — Harden the inference server (4 weeks)

### Week 1 — Metrics, observability & benchmark harness
- [x] 1. `metrics` module: TTFT, ITL, latency, tokens, counters, percentiles
      (`inference-server/src/inference_server/metrics.py`)
- [x] 2. `GET /metrics` endpoint (p50/p95/p99 windows) + middleware timing
- [x] 3. `benchmarks/` concurrency-ramp harness (workspace package: stream +
      non-stream, reports latency/TTFT/ITL/throughput + server metrics)
- [x] 4. Verify rate limiting under load; note impact (unit tests +
      `by_status` in metrics)
- [x] 5. `docs/benchmarks/baseline.md` — honest starting numbers (headline:
      single-client streaming is fine; concurrency collapses)

### Week 2 — Continuous batching & KV caching
- [x] 6. Batch multiple queued jobs into one model call
- [ ] 7. Continuous-batching semantics (mid-stream add/remove) — **blocked** on a
      runtime change (high-level llama-cpp manages a per-request KV cache; no
      multi-sequence API). Documented, not faked.
- [ ] 8. Prefix caching across requests — **assessed**; same runtime blocker.
      See `docs/benchmarks/batching-vs-baseline.md`.
- [x] 9. Study `scratch-inference/kv_cache.py` (prefill vs decode) → notes at
      `docs/notes/kv-cache-prefill-decode.md`
- [x] 10. Re-baseline with admission control; write `docs/benchmarks/batching-vs-baseline.md`
- [x] 11. Admission control (protect the box under overload) — `MAX_IN_FLIGHT`
      capacity; rejects excess with 503 + `Retry-After`. Live-verified: 8
      concurrent → 2 accepted, 6 cleanly rejected.
> **Week-2 outcome:** admission control (A1) is the shipped, verifiable win — the
> box no longer drowns under load. Token-level continuous batching (B1/B2) and
> prefix caching (B3) are *deliberately* documented as blocked on switching to a
> runtime that exposes multi-sequence decode, rather than building a fake batch
> layer.

### Week 3 — Router, quantization & evidence write-ups
- [ ] 12. `router/` package: cost/latency/quality-aware selection + fallback
- [ ] 13. Wire router into chat router; log routing decisions
- [ ] 14. Quantization sweep (Q4 vs Q8) for the same model
- [ ] 15. Publish 2 evidence write-ups (see `ROADMAP.md` Q1)
- [ ] 16. Make model engine pluggable (llama.cpp / scratch)

### Week 4 — Reliability, deployability & FDE story
- [ ] 17. Container/Nixpacks build still green with new packages
- [ ] 18. Failure modes: graceful shutdown, timeouts, backpressure, 503s
- [ ] 19. FDE mini-report: the "100M tokens/day @ p95 TTFT" whiteboard
- [ ] 20. Final benchmark report + consolidated narrative

---

## Portfolio backlog (long-form, beyond Month 1)

- [x] **Inference API** — OpenAI-compatible server (chat, embeddings, streaming,
      tools, auth, rate-limit, deploy). *See `inference-server/`.*
- [x] **Scheduler** — priority-queue request scheduler (library). *Ref and
      hardening continues in Week 2 (`scheduler/`).*
- [x] **From-scratch inference reference** — BPE tokenizer, KV cache, transformer
      in numpy (`scratch-inference/`). Used as a learning/pluggable reference.
- [-] **Document intelligence / OCR-to-enterprise** — FDE showcase. Deferred past
      Month 1 (was flagged as a strong FDE portfolio project).
- [-] **Evals + error analysis platform** — deferred; build the minimal subset
      needed to measure the Week 1-4 benchmarks only.
- [-] **Production agent with verifiers** — deferred past Month 1.
- [-] **Coding agent (OpenHands-style)** — deferred past Month 1.
- [-] **LLM router** — *pulled into Week 3* as the routing engine (R1-R2).
- [-] **Distributed / multi-node serving** — post Month 1.
- [-] **Monitoring / dashboards** — post Month 1.
