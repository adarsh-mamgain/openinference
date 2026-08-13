"""Weight loading and a high-level inference engine.

``load_weights`` reads a ``model.safetensors`` file into a dict of float32
numpy arrays (decoding the bfloat16 bytes with numpy; the *structure* of the
file is parsed here — no safetensors python API is used beyond reading bytes).

``InferenceEngine`` ties together the BPE tokenizer, the from-scratch
transformer model and the KV cache, exposing a chat-completion-style interface:
``generate(messages)`` and ``generate_chat_text(messages)``.
"""

import json
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from scratch_inference.bpe import BPETokenizer
from scratch_inference.kv_cache import KVCache
from scratch_inference.model import ScratchModel


def _bf16_to_f32(bytes_view: bytes) -> np.ndarray:
    """Decode raw bfloat16 bytes into float32 numpy array (bit manipulation)."""
    arr = np.frombuffer(bytes_view, dtype=np.uint16)
    # bf16 -> f32: shift 16 bits left, then reinterpret.
    f32_uint = arr.astype(np.uint32) << 16
    return f32_uint.view(np.float32).copy()


def load_weights(path: str | Path) -> dict[str, np.ndarray]:
    """Load all tensors from a safetensors file as float32 numpy arrays."""
    path = Path(path)
    with open(path, "rb") as f:
        header_len = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(header_len))
        offset = 8 + header_len

        tensors: dict[str, np.ndarray] = {}
        for name, info in header.items():
            if name == "__metadata__":
                continue
            shape = tuple(info["shape"])
            dtype = info["dtype"]
            data_offset = info["data_offsets"]
            f.seek(offset + data_offset[0])
            raw = f.read(data_offset[1] - data_offset[0])

            if dtype == "BF16":
                arr = _bf16_to_f32(raw)
            elif dtype in ("F32", "F16", "U8", "U16", "U32", "I64", "I32", "U64"):
                np_dtype = {"F32": np.float32, "F16": np.float16, "U8": np.uint8,
                            "U16": np.uint16, "U32": np.uint32, "I64": np.int64,
                            "I32": np.int32, "U64": np.uint64}[dtype]
                arr = np.frombuffer(raw, dtype=np_dtype).astype(np.float32)
            else:
                raise ValueError(f"Unsupported dtype: {dtype}")
            tensors[name] = arr.reshape(shape)
    return tensors


@dataclass
class InferConfig:
    n_layers: int = 24
    hidden: int = 896
    n_heads: int = 14
    n_kv_heads: int = 2
    intermediate: int = 4864
    rope_theta: float = 1_000_000.0
    max_seq: int = 2048
    rms_eps: float = 1e-6
    eos_id: int = 151645  # <|im_end|>


_IM_START = "<|im_start|>"
_IM_END = "<|im_end|>"


class InferenceEngine:
    """Chat-completion front-end over the from-scratch model + tokenizer."""

    def __init__(
        self,
        weight_path: str | Path,
        tokenizer_path: str | Path,
        config: InferConfig | None = None,
    ) -> None:
        self.cfg = config or InferConfig()
        self.tokenizer = BPETokenizer(tokenizer_path)
        self.model = ScratchModel(
            weights=load_weights(weight_path),
            n_layers=self.cfg.n_layers,
            hidden=self.cfg.hidden,
            n_heads=self.cfg.n_heads,
            n_kv_heads=self.cfg.n_kv_heads,
            intermediate=self.cfg.intermediate,
            rope_theta=self.cfg.rope_theta,
            max_seq=self.cfg.max_seq,
            rms_eps=self.cfg.rms_eps,
        )

    def generate(
        self,
        messages: list[dict],
        max_new_tokens: int = 64,
        temperature: float = 0.8,
        top_k: int = 40,
        top_p: float = 0.9,
        seed: int | None = None,
    ) -> list[int]:
        prompt = self._build_prompt_tokens(messages)
        cache = KVCache(self.cfg.n_layers)
        return self.model.generate(
            input_ids=prompt,
            eos_id=self.cfg.eos_id,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            seed=seed,
            cache=cache,
        )

    def generate_chat_text(
        self,
        messages: list[dict],
        max_new_tokens: int = 64,
        temperature: float = 0.8,
        top_k: int = 40,
        top_p: float = 0.9,
        seed: int | None = None,
    ) -> str:
        ids = self.generate(messages, max_new_tokens, temperature, top_k, top_p, seed)
        return self.tokenizer.decode(ids)

    def _build_prompt_tokens(self, messages: list[dict]) -> list[int]:
        tokens: list[int] = []
        for m in messages:
            tokens.extend(self.tokenizer.encode_text(f"{_IM_START}{m['role']}\n{m['content']}{_IM_END}"))
        tokens.extend(self.tokenizer.encode_text(f"{_IM_START}assistant\n"))
        return tokens
