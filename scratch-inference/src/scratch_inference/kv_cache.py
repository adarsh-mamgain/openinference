"""An explicit key/value cache for autoregressive decoding.

Attention over a sequence computes ``Q K^T`` for every token. In decoding we
generate one new token at a time and, without a cache, would recompute attention
for *all* previous tokens every step. A KV cache stores the key/value tensors of
each layer from prior steps and only computes keys/values for the newest token,
reusing the cached history. This makes decode O(1) work per step per layer
instead of O(sequence) and demonstrates why every serving engine has one.

Implementation notes:

* One cache per layer (for grouped-query attention we cache the *grouped* K/V
  projections, not the repeated heads).
* Pre-allocated numpy arrays grown as needed to avoid copies on every append.
* ``slice_into`` / ``from_logits`` helpers keep the model code simple: a single
  forward pass for multiple tokens (prefill) or one token (decode) both work.
"""

from dataclasses import dataclass, field

import numpy as np


def _ensure(arr: np.ndarray | None, shape_tail: tuple, dtype, needed: int) -> np.ndarray:
    """Return an array with at least ``needed`` rows, copying existing content."""
    if arr is not None and needed <= arr.shape[0]:
        return arr
    capacity = max(64, needed * 2)
    new = np.empty((capacity,) + shape_tail, dtype=dtype)
    if arr is not None:
        new[: arr.shape[0]] = arr
    return new


@dataclass
class LayerKV:
    """Key/value history for one transformer layer."""

    k: np.ndarray = None  # (capacity, kv_heads, head_dim)
    v: np.ndarray = None
    size: int = 0

    def append(self, k_new: np.ndarray, v_new: np.ndarray) -> None:
        """Append new keys/values of shape (seq, kv_heads, head_dim)."""
        n = k_new.shape[0]
        tail = k_new.shape[1:]
        self.k = _ensure(self.k, tail, k_new.dtype, self.size + n)
        self.v = _ensure(self.v, tail, v_new.dtype, self.size + n)
        self.k[self.size : self.size + n] = k_new
        self.v[self.size : self.size + n] = v_new
        self.size += n

    def get(self) -> tuple[np.ndarray, np.ndarray]:
        return self.k[: self.size], self.v[: self.size]

    def reset(self) -> None:
        self.size = 0


@dataclass
class KVCache:
    """The full cache: one :class:`LayerKV` per layer."""

    n_layers: int
    layers: list[LayerKV] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.layers = [LayerKV() for _ in range(self.n_layers)]

    def append(self, layer: int, k: np.ndarray, v: np.ndarray) -> None:
        self.layers[layer].append(k, v)

    def get(self, layer: int) -> tuple[np.ndarray, np.ndarray]:
        return self.layers[layer].get()

    def size(self, layer: int) -> int:
        return self.layers[layer].size

    def reset(self) -> None:
        for layer in self.layers:
            layer.reset()
