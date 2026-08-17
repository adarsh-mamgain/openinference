# "Why my server is N× slower than vLLM" — an honest, measured answer

> A 0.5B model on a 4-core CPU is not vLLM on GPUs. But "N× slower" isn't a
> number until you say what N is and where the time goes. This note answers that
> with the repo's actual benchmark data and the three structural causes — all
> deliberate trade-offs of the single-worker CPU design, none of them bugs.

## The comparison (real numbers, this repo)

Reference workloads: Qwen2.5-0.5B-Instruct, streaming, `benchmarks/run.py` and
`sweep.py` on a 4-core CPU box.

| Metric | This server (CPU) | What a GPU/vLLM-style stack typically delivers |
|--------|------------------|------------------------------------------------|
| Tokens/sec (single stream) | ~6–10 | 10–100× higher decode bandwidth |
| Inter-token latency (ITL) | ~58–132 ms | ~10–30 ms and falling with batch overlap |
| Concurrent streams | collapses past 1–2 | thousands of sequences in a single batch |

If vLLM-class decode is ~50 tokens/sec→decodes 0.5B in GPU at thousands of
tok/s, the honest ratio is **roughly 100× on raw generation, and the *shape* of
the collapse under concurrency is different in kind**: this server *loses*
capacity (connection errors at concurrency 4) where vLLM *gains* throughput by
batching more sequences into each forward pass.

## Why. Three causes, each measured or structural.

### 1. The hardware (10×-100×, not fixable in code)

Decode is memory-bandwidth bound: every forward pass reads the entire weight
matrix for one new token (`scratch-inference/kv_cache.py` — prefill is
`O(seq·params)`, decode is `O(params)` per token). A consumer CPU delivers tens
of GB/s; a GPU delivers terabytes/s. This is **not** the interesting cause — it
just sets the floor.

### 2. Single-sequence decode — no continuous batching (the interesting cause)

vLLM/SGLang's core trick is **continuous batching**: many sequences share one
forward pass, so per-token cost *per sequence* falls as the batch fills, and
arrivals join mid-stream. This server executes one stream per model context on a
priority-queued worker pool, so:

- the box is **memory-idle while a stream is in flight** — one token at a time;
- 2+ concurrent streams **starve each other** (measured: concurrency=2 produced
  200s with zero streamed tokens, concurrency=4 dropped connections) instead of
  sharing a batch;
- throughput **collapses with concurrency** instead of rising.

This is exactly the win admission control couldn't buy: `MAX_IN_FLIGHT`
bounded *how much* die (`batching-vs-baseline.md`: 2 served, 6 clean 503s) —
it didn't make the box *faster*, because speed at concurrency needs
multi-sequence decode in the runtime.

### 3. The runtime boundary (the honest block)

The high-level llama.cpp API (`create_chat_completion`) manages a per-request
KV cache; there is no `llama_batch`-style multi-sequence path exposed at this
level. So continuous batching and prefix caching are **not** implemented
because the current runtime can't do them — not as a feature flag I forgot to
flip. That's internalized in `docs/benchmarks/batching-vs-baseline.md` and
`docs/notes/kv-cache-prefill-decode.md`. The next milestone is switching the
exec model to one that exposes multi-sequence decode.

## What's actually good (so the comparison isn't all one-sided)

- **Single-stream latency is sane**: TTFT p50 ~110–360 ms — prefill of short
  prompts is cheap; tokens arrive at a steady ~60–130 ms cadence. For
  interactive single-user use on a CPU this is usable.
- **Overload is contained**: admission control turns "server unresponsive"
  into crisp 503s with `Retry-After` (`batching-vs-baseline.md`).
- **The routers work**: the quant sweep (`quant-sweep.md`) and routing layer
  let the server answer *which model, why*, on this hardware — that's the
  cost engineering a real deployment wants on top of a fast engine.

## The honest verdict

The N is **~100×** for raw generation and **"different in kind"** under load —
and the reason isn't "I wrote a bad server." It's: CPU hardware, no
multi-sequence batching, and a runtime that caps that. The fix is a known,
bounded next step (pluggable exec engine exposing batch decode, ROADMAP item
16). A demo says "it works"; this write-up says "I know where the last 100×
went and how to spend it."