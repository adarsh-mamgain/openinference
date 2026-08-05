"""Local model backend powered by llama-cpp-python.

Loads a quantized GGUF model (e.g. Qwen2.5-0.5B-Instruct Q4_K_M) and serves
chat completions + streaming directly on CPU. No external GPU or API needed.

The model object is created lazily on first use so the server can start even
when the model file is missing (e.g. before `scripts/download-model.sh` runs).
"""

from pathlib import Path
from typing import Iterator

from inference_server.config import settings
from inference_server.mock_model import count_tokens, generate, stream_chunks
from inference_server.schemas import Message


class LocalModel:
    """Thin wrapper around a llama-cpp Llama instance."""

    def __init__(self, model_path: str, n_ctx: int, n_threads: int) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._llm = None

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
        return self._llm

    @property
    def available(self) -> bool:
        return Path(self.model_path).is_file()

    def count_tokens(self, text: str) -> int:
        try:
            return len(self._load().tokenize(text.encode("utf-8")))
        except Exception:
            return count_tokens(text)

    def generate(self, messages: list[Message], max_tokens: int) -> str:
        if not self.available:
            return generate(messages, max_tokens)[0]

        llm = self._load()
        result = llm.create_chat_completion(
            messages=[m.model_dump(exclude_none=True) for m in messages],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return result["choices"][0]["message"]["content"] or ""

    def stream(self, messages: list[Message], max_tokens: int) -> Iterator[str]:
        """Yield text deltas as the model generates them."""
        if not self.available:
            for chunk in stream_chunks(messages, max_tokens):
                yield chunk
            return

        llm = self._load()
        stream = llm.create_chat_completion(
            messages=[m.model_dump(exclude_none=True) for m in messages],
            max_tokens=max_tokens,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            text = delta.get("content", "")
            if text:
                yield text


# Module-level singleton shared across requests.
model = LocalModel(
    model_path=settings.model_path,
    n_ctx=settings.model_ctx,
    n_threads=settings.model_threads,
)


def use_real_model() -> bool:
    """Whether the local model file is present and should be used."""
    return settings.model_backend == "local" and model.available
