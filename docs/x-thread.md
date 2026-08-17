# X thread draft — "I built and benchmarked my own LLM inference server"

A ready-to-post X (Twitter) thread. Under each `▶` is one tweet (cut anything
you feel is too long). Companion numbers are all real, from the repo's
benchmarks.

---

**Tweet 1 — hook**

> Everyone can call an LLM API. Almost nobody can explain why their server
> stalls at 2 concurrent requests, or point at the exact line that admits the
> 3rd. So I built my own OpenAI-compatible server and benchmarked the hell out of
> it. Here's what "knowing inference" looks like. 🧵

**Tweet 2 — what it is**

> `POST /v1/chat/completions` — OpenAI shape, streaming SSE, tools, embeddings,
> auth, rate limits. Runs a real 0.5B model (llama.cpp, CPU) behind a
> priority-queue scheduler so requests don't just "arrive at the model."

**Tweet 3 — the scheduler (why it matters)**

> A request doesn't touch the model directly. It goes: auth → rate-limit →
> router → bounded priority queue → worker pool → model.
>
> The queue is the whole job. Unbounded queues turn "slow" into "dead."

**Tweet 4 — admission control**

> But the queue alone isn't enough. Above capacity the server must say NO —
> loudly, cleanly, repeatedly.
>
> `in_flight + queued >= max_in_flight` → HTTP 503 + `Retry-After: 2`.
>
> Live: 8 concurrent → 2 served, 6 clean 503s, box still answers /health.
> That's admission control, same family as vLLM's `--max-num-seqs`.

**Tweet 5 — the numbers (baseline)**

> Then we measured the box (before any optimization). Single client streaming,
> Qwen 0.5B, CPU:
>
> • TTFT ~110–360 ms (first token)
> • ITL ~58–132 ms (token cadence)
> • ~6–10 tok/s
>
> Sound fine? Here's the ugly part.

**Tweet 6 — the collapse**

> Under concurrency, the single-worker architecture collapses:
>
> concurrency=1 → healthy
> concurrency=2 → 200s with ZERO streamed tokens
> concurrency=4 → connection errors
>
> The harness exposed the ceiling. That's why you build benchmarks first.

**Tweet 7 — metrics matter (what TTFT/ITL mean)**

> The metrics that matter:
>
> • TTFT = prefill cost (prompt) — users judge "is it alive" by this
> • ITL = decode cost (per token) — the dominant cost at small ctx
> • p95/p99 = tail, not average — SLOs are written in percentiles
>
> We record all of it: `GET /metrics` → p50/p95/p99 + by_status.

**Tweet 8 — the router (Week 3)**

> This month I added routing on top: the same 0.5B model served at two
> precisions (Q4_K_M vs Q8_0), and the server chooses per request:
>
> score = (w_q·quality + w_l·latency + w_c·cost) / Σw
>
> Every decision carries a reason string + health-fed fallback. If a route
> fails repeatedly, it goes on a 30s cooldown instead of getting hammered.

**Tweet 9 — the quantization reality**

> The sweep both quants with real numbers:
>
> Q4: 491M on disk, quality 0.55, ~10 tok/s
> Q8: 676M (+37%), quality 0.9, ~9.8 tok/s
>
> Real result: at 0.5B scale Q8 buys little measurable quality at +37% memory.
> The router is right to default to Q4. That's the cost/latency engineering.

**Tweet 10 — why it's slower than vLLM**

> "Why is this N× slower than vLLM?" — the honest answer:
>
> 1. CPU vs GPU memory bandwidth (~10–100×)
> 2. Single-stream decode, no batching (the interesting part)
> 3. Runtime API doesn't expose multi-sequence decode (yet)
>
> Slower isn't unearned — it's *measured and understood*.

**Tweet 11 — the honest gap**

> The one thing I refuse to fake: continuous batching & prefix caching.
>
> The high-level llama.cpp API manages a per-request KV cache I can't extend,
> so real batching needs a runtime that exposes multi-sequence decode. I wrote
> it down as a genuine block instead of a pretend batch layer.

**Tweet 12 — what it's really about**

> The whole project is evidence, not vibes:
>
> • every number above came from a benchmark harness in the repo
> • a from-scratch KV cache in numpy teaches prefill vs decode
> • 29 tests lock the behavior in
>
> Repo: github.com/anomalyco/openinference

**Tweet 13 — closing**

> "I can call an LLM API" ≈ "I can drive a car."
>
> This is learning to rebuild the engine. Build your own. The weirdest part is
> how fast you stop treating inference as magic.
>
> /end 🧵

---

## Posting notes

- Replace the repo URL with the actual public URL before posting.
- Attach `docs/explainer.md` diagrams (or screenshots of `GET /metrics`) as
  image alt-text on tweets 5, 7, 9.
- Trim tweets >280 chars: the numbers lists are the first candidates to compress.
- If you'd rather publish the long-form versions: `docs/evidence/server-from-scratch.md`
  and `docs/evidence/slower-than-vllm.md` are exactly the two blog posts this
  thread tee's up.