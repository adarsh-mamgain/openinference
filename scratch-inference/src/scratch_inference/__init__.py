"""scratch-inference — an inference stack built from scratch.

Implements the full inference path without a serving engine:

* ``bpe`` — a byte-level BPE tokenizer (Qwen/GPT-2 style) built from
  ``tokenizer.json``: NFC normalize, GPT-2 pre-tokenization, greedy merges.
* ``kv_cache`` — an explicit key/value cache for autoregressive decoding.
* ``model`` — the transformer forward pass (RMSNorm, RoPE, GQA attention,
  SwiGLU FFN) plus greedy/top-k/top-p sampling.
* ``loader`` — reads ``model.safetensors`` weights and exposes them as the
  numpy tensors the forward pass consumes.

Only numpy and safetensors are used (for loading bytes); the neural-network
math itself is implemented here.
"""
