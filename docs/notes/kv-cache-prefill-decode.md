# Notes — KV cache: prefill vs decode

> Companion to the from-scratch implementation in
> [`../scratch-inference/src/scratch_inference/kv_cache.py`](../../scratch-inference/src/scratch_inference/kv_cache.py)
> and the transformer forward pass in `model.py`. These are the notes referenced
> by Week 2 of the roadmap.

## The one idea that matters

Autoregressive decoding is sequential: to produce token *N* you must first have
tokens *0..N-1*. A naive implementation recomputes attention over the whole
history at every step — O(sequence) work per token, O(sequence²) overall.

The KV cache stores the key and value projections of **every previous token**,
per layer. Then each new decode step only computes keys/values for the *new*
token and reuses the cached history: **O(1) work per step per layer** instead of
O(sequence).

`scratch_inference/kv_cache.py` shows this concretely:

- `LayerKV` holds the growing `(capacity, kv_heads, head_dim)` arrays per layer;
- `append()` writes new keys/values and bumps `size`;
- decoding calls `(previous keys) + new key` → full attention without recompute.

## Prefill ≠ decode

| Phase | What happens | Work |
|-------|--------------|------|
| **Prefill** | Process the whole prompt in one forward pass, populating the KV cache | O(sequence) — parallelizable across tokens |
| **Decode** | One token at a time, each step only re-reads cached keys | O(1) per step, serial |

This is why TTFT is dominated by **prefill** (first token waits for the whole
prompt to be cached) and how inter-token latency (ITL/TPOT) reflects **decode**.
Real serving engines (vLLM, SGLang) are engineered to make both fast: prefill is
bursty/parallelizable, decode is latency-bound.

## Why it matters for OpenInference

1. **Baseline finding:** our CPU server's ~60–130 ms inter-token latency is
   decode-bound (24 layers × decode step on 2 threads). KV-cache efficiency
   directly caps this.
2. **The Week-2 goal:** sharing a KV cache across *multiple* requests is what
   enables **continuous batching** — multiple sequences advance through decode
   together instead of one at a time.
3. **Prefix caching** is the same idea applied to the *front* of the cache: if
   many requests share a system-prompt prefix, cache it once and only compute the
   varying suffix.

## Constraint with the current runtime

The served model goes through `llama-cpp-python`'s high-level
`create_chat_completion` API, which manages its own KV cache per request and
does **not** expose multi-sequence continuous batching or prefix reuse through
that interface. True continuous batching/paged attention requires the
lower-level `llama_batch` API or a custom runtime — which is why this month's
server-side wins are (a) admission control to stop oversubscription and (b) a
clean measurement harness to quantify the remaining gap vs vLLM/SGLang, rather
than pretending a fake batch layer exists.
