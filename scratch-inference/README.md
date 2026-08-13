# scratch-inference

An inference stack built **from scratch** with numpy: a byte-level BPE
tokenizer, a transformer forward pass, and an explicit KV cache. It runs the
real Qwen2.5-0.5B-Instruct weights (bfloat16 safetensors) entirely on CPU
without a serving engine like llama.cpp — the neural-network math is implemented
here.

```
text → BPE tokenizer → embed → 24 × (RMSNorm → GQA attention → SwiGLU FFN)
      → LM head → sample → text
                            (KVCache reused across decode steps)
```

## What it implements

- **`bpe.py`** — byte-level BPE (GPT-2/Qwen style) from `tokenizer.json`:
  NFC normalize, GPT-2 pre-tokenization regex, greedy merges, special tokens.
- **`kv_cache.py`** — an explicit per-layer key/value cache so decoding is
  O(1) work per step instead of recomputing attention over the whole history.
- **`model.py`** — the transformer: RMSNorm, RoPE, grouped-query attention
  (14 Q heads / 2 KV heads), SwiGLU FFN, tied embeddings; greedy + top-k/top-p
  sampling.
- **`loader.py`** — reads `model.safetensors` (bfloat16) into float32 numpy
  tensors and exposes an `InferenceEngine` chat front-end.

## Files

- `config.json` — model architecture (from Hugging Face)
- `tokenizer.json` — BPE vocab + merges + special tokens
- `model.safetensors` — Qwen2.5-0.5B-Instruct weights (~988MB, bfloat16)

## Setup

```bash
uv sync --all-packages        # from the monorepo root (uv workspace)
```

## Use

```python
from scratch_inference.loader import InferenceEngine

engine = InferenceEngine(
    weight_path="src/scratch_inference/data/model.safetensors",
    tokenizer_path="src/scratch_inference/data/tokenizer.json",
)

print(engine.generate_chat_text([{"role": "user", "content": "Say hello."}]))
```

## Workspace

Part of the `openinference` monorepo uv workspace (alongside `inference-server`
and `scheduler`), so it can be wired in as the from-scratch runtime alternative
to llama.cpp.
