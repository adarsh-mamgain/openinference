"""The transformer forward pass, built from scratch with numpy.

Implements a Qwen2-style causal language model (the architecture of
Qwen2.5-0.5B-Instruct) and decodes tokens autoregressively with an explicit
:class:`KVCache`:

* RMSNorm (pre-norm)
* Rotary position embeddings (RoPE, half-rotation)
* Grouped-query attention (GQA): 14 query heads, 2 key/value heads
* SwiGLU feed-forward network
* Tied input/output embedding matrix

Only numpy is used for the math. Weights are float32 arrays provided by the
loader; this module performs the neural-network computation itself.
"""

from dataclasses import dataclass

import numpy as np

from scratch_inference.kv_cache import KVCache


# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #


def rms_norm(x: np.ndarray, weight: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """RMSNorm over the last axis (per-token)."""
    variance = np.mean(x.astype(np.float64) ** 2, axis=-1, keepdims=True)
    x_norm = x * np.reciprocal(np.sqrt(variance + eps))
    return x_norm * weight


def _rope_cache(head_dim: int, max_seq: int, theta: float) -> tuple[np.ndarray, np.ndarray]:
    """Precompute cos/sin for half-split RoPE for every position up to max_seq."""
    half = head_dim // 2
    inv_freq = 1.0 / (theta ** (np.arange(0, half, dtype=np.float64) / half))
    positions = np.arange(max_seq, dtype=np.float64)
    freqs = np.outer(positions, inv_freq)  # (max_seq, half)
    cos = np.cos(freqs).astype(np.float32)
    sin = np.sin(freqs).astype(np.float32)
    return cos, sin


def apply_rope(q: np.ndarray, k: np.ndarray, cos, sin, offset: int) -> tuple[np.ndarray, np.ndarray]:
    """Apply half-split RoPE. q,k shape (seq, heads, head_dim). offset = start pos."""
    half = q.shape[-1] // 2
    pos = slice(offset, offset + q.shape[0])
    cos_ = cos[pos][:, None, :]  # (seq, 1, half) applied to each half
    sin_ = sin[pos][:, None, :]

    def rotate_first_half(x):
        x1 = x[..., :half]
        x2 = x[..., half:]
        rotated = np.concatenate([-x2, x1], axis=-1)  # half-split rotation
        return x * np.concatenate([cos_, cos_], axis=-1) + rotated * np.concatenate([sin_, sin_], axis=-1)

    return rotate_first_half(q), rotate_first_half(k)


@dataclass
class LayerWeights:
    input_layernorm: np.ndarray
    q_proj: np.ndarray
    q_bias: np.ndarray
    k_proj: np.ndarray
    k_bias: np.ndarray
    v_proj: np.ndarray
    v_bias: np.ndarray
    o_proj: np.ndarray
    post_attention_layernorm: np.ndarray
    gate_proj: np.ndarray
    up_proj: np.ndarray
    down_proj: np.ndarray


def attention(
    x: np.ndarray,
    w: LayerWeights,
    cache: KVCache,
    layer: int,
    cos, sin,
    offset: int,
    n_heads: int,
    n_kv_heads: int,
    head_dim: int,
) -> np.ndarray:
    """GQA self-attention with the KV cache. x: (seq, hidden)."""
    seq = x.shape[0]

    q = x @ w.q_proj.T + w.q_bias  # (seq, n_heads*head_dim)
    k = x @ w.k_proj.T + w.k_bias  # (seq, n_kv_heads*head_dim)
    v = x @ w.v_proj.T + w.v_bias

    q = q.reshape(seq, n_heads, head_dim)
    k = k.reshape(seq, n_kv_heads, head_dim)
    v = v.reshape(seq, n_kv_heads, head_dim)

    q, k = apply_rope(q, k, cos, sin, offset)

    # Store new k/v for this step in the cache.
    cache.append(layer, k, v)
    full_k, full_v = cache.get(layer)  # (past+n, n_kv, hd)

    # Repetition for grouped-query attention: each KV head serves several Q heads.
    repeat = n_heads // n_kv_heads
    full_k = np.repeat(full_k, repeat, axis=1)  # (N, n_heads, hd)
    full_v = np.repeat(full_v, repeat, axis=1)

    # scores: (seq, n_heads, N)
    scores = np.einsum("qhd,khd->qhk", q, full_k) / np.sqrt(head_dim)
    N = full_k.shape[0]
    # Causal mask over absolute positions: a query at absolute position p may
    # attend only to keys with position <= p. Cached past keys are always
    # attendable (they have smaller positions), only future keys are masked.
    k_pos = np.arange(N)
    q_pos = offset + np.arange(seq)
    mask = k_pos[None, :] > q_pos[:, None]  # (seq, N) True where masked
    scores = np.where(mask[:, None, :], -1e30, scores)
    probs = np.exp(scores - scores.max(axis=-1, keepdims=True))
    probs = probs / probs.sum(axis=-1, keepdims=True)

    out = np.einsum("qhk,khd->qhd", probs, full_v)  # (seq, n_heads, hd)
    out = out.reshape(seq, n_heads * head_dim)
    return out @ w.o_proj.T


def feed_forward(x: np.ndarray, w: LayerWeights) -> np.ndarray:
    """SwiGLU: silu(x @ gate) * (x @ up) @ down."""
    gate = x @ w.gate_proj.T
    up = x @ w.up_proj.T
    silu = gate * (1.0 / (1.0 + np.exp(-gate)))  # SiLU
    hidden = silu * up
    return hidden @ w.down_proj.T


# --------------------------------------------------------------------------- #
# The model
# --------------------------------------------------------------------------- #


class ScratchModel:
    """A from-scratch Qwen2-style model that decodes tokens with a KV cache."""

    def __init__(
        self,
        weights: dict[str, np.ndarray],
        n_layers: int = 24,
        hidden: int = 896,
        n_heads: int = 14,
        n_kv_heads: int = 2,
        intermediate: int = 4864,
        rope_theta: float = 1_000_000.0,
        max_seq: int = 2048,
        rms_eps: float = 1e-6,
    ) -> None:
        self.embed_tokens = weights["model.embed_tokens.weight"]
        self.vocab_size = self.embed_tokens.shape[0]

        self.head_dim = hidden // n_heads
        self.layers: list[LayerWeights] = []
        for i in range(n_layers):
            p = f"model.layers.{i}."
            self.layers.append(
                LayerWeights(
                    input_layernorm=weights[p + "input_layernorm.weight"],
                    q_proj=weights[p + "self_attn.q_proj.weight"],
                    q_bias=weights[p + "self_attn.q_proj.bias"],
                    k_proj=weights[p + "self_attn.k_proj.weight"],
                    k_bias=weights[p + "self_attn.k_proj.bias"],
                    v_proj=weights[p + "self_attn.v_proj.weight"],
                    v_bias=weights[p + "self_attn.v_proj.bias"],
                    o_proj=weights[p + "self_attn.o_proj.weight"],
                    post_attention_layernorm=weights[p + "post_attention_layernorm.weight"],
                    gate_proj=weights[p + "mlp.gate_proj.weight"],
                    up_proj=weights[p + "mlp.up_proj.weight"],
                    down_proj=weights[p + "mlp.down_proj.weight"],
                )
            )

        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads
        self.intermediate = intermediate
        self.rms_eps = rms_eps

        # Precompute RoPE tables once.
        cos, sin = _rope_cache(self.head_dim, max_seq, rope_theta)
        self._cos = cos
        self._sin = sin

        # The tie_word_embeddings model reuses the embedding matrix as the LM head.
        self.lm_head = self.embed_tokens

    def _forward(
        self, token_ids: np.ndarray, cache: KVCache, offset: int
    ) -> np.ndarray:
        """One forward step: token_ids (seq,) -> logits (seq, vocab)."""
        x = self.embed_tokens[token_ids].astype(np.float32)  # (seq, hidden)

        for i, w in enumerate(self.layers):
            r = rms_norm(x, w.input_layernorm, self.rms_eps)
            a = attention(r, w, cache, i, self._cos, self._sin, offset,
                          self.n_heads, self.n_kv_heads, self.head_dim)
            x = x + a.astype(x.dtype)

            r = rms_norm(x, w.post_attention_layernorm, self.rms_eps)
            f = feed_forward(r, w)
            x = x + f.astype(x.dtype)

        x = rms_norm(x, self.layers[-1].input_layernorm, self.rms_eps)
        logits = x @ self.lm_head.T  # (seq, vocab)
        return logits

    def generate(
        self,
        input_ids,
        eos_id: int,
        max_new_tokens: int = 64,
        temperature: float = 0.8,
        top_k: int = 40,
        top_p: float = 0.9,
        seed: int | None = None,
        cache: KVCache | None = None,
    ) -> list[int]:
        """Greedy/sampled autoregressive generation with a KV cache."""
        rng = np.random.default_rng(seed)
        cache = cache or KVCache(len(self.layers))
        ids = list(input_ids)

        # Prefill: process the whole prompt, get next-token logits.
        logits = self._forward(np.asarray(ids, dtype=np.int64), cache, offset=0)
        next_logits = logits[-1]

        for _ in range(max_new_tokens):
            probs = self._sampling_probs(next_logits, temperature, top_k, top_p)
            nxt = int(rng.choice(len(probs), p=probs)) if temperature > 0 else int(np.argmax(next_logits))
            ids.append(nxt)
            if nxt == eos_id:
                break
            # Small epsilon to keep cache dtype consistent across steps.
            logits = self._forward(
                np.asarray([nxt], dtype=np.int64), cache, offset=len(ids) - 1
            )
            next_logits = logits[0]
        return ids

    def _sampling_probs(self, logits, temperature, top_k, top_p) -> np.ndarray:
        logits = logits.astype(np.float64)
        if temperature > 0:
            logits = logits / temperature
        probs = np.exp(logits - logits.max())
        probs = probs / probs.sum()

        if top_k > 0:
            indices = np.argpartition(probs, -top_k)[-top_k:]
            keep = np.zeros_like(probs)
            keep[indices] = probs[indices]
            probs = keep
            probs = probs / probs.sum()

        if 0.0 < top_p < 1.0:
            order = np.argsort(probs)[::-1]
            sorted_probs = probs[order]
            cum = np.cumsum(sorted_probs)
            cutoff = np.searchsorted(cum, top_p, side="left")
            keep_idx = order[: max(cutoff + 1, 1)]
            keep = np.zeros_like(probs)
            keep[keep_idx] = probs[keep_idx]
            probs = keep
            probs = probs / probs.sum()
        return probs
