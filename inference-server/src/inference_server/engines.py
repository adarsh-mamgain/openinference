"""Pluggable model engine — the interface the server serves through.

Everything that runs a model (the scheduler's exec models, the chat router's
token counting, the landing page's availability check) talks to a
:class:`ModelEngine`, never to llama.cpp or numpy directly. Choosing a backend
is configuration, not a code edit: ``settings.model_backend`` selects between
``local`` (llama.cpp GGUF) and ``scratch`` (the from-scratch numpy stack).

The contract is deliberately the shape the scheduler already consumes:

* ``available`` — can this engine serve right now (files present)?
* ``generate(messages, max_tokens, tools)`` -> ``(content, tool_calls, finish)``
* ``stream(messages, max_tokens, tools)`` -> iterations of text deltas
* ``count_tokens(text)`` — model-accurate token count

Swift wrappers that just adapt an existing library (llama.cpp) or expose the
reference stack (scratch) live right here; the server never imports a backend
library directly.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator

logger = logging.getLogger(__name__)


class ModelEngine(ABC):
    """The operations a serving engine must expose to the scheduler + router."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Whether the engine can serve now (e.g. model files present)."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Return the exact token count for *text* using this model's tokenizer."""

    @abstractmethod
    def count_tokens_messages(self, messages: list) -> int:
        """Return the approximate prompt-token count for a message list."""

    @abstractmethod
    def generate(
        self,
        messages: list,
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> tuple[str | None, list | None, str]:
        """Run a chat completion: return ``(content, tool_calls, finish_reason)``.

        ``tool_calls`` is ``None`` when the engine doesn't support tools (the
        from-scratch backend), which callers already handle.
        """

    @abstractmethod
    def stream(
        self,
        messages: list,
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> Iterator[str]:
        """Yield text deltas as the model generates them."""


class ScratchEngine(ModelEngine):
    """Adapter over :class:`scratch_inference.loader.InferenceEngine`.

    Exposes the from-scratch numpy stack (BPE tokenizer + transformer + KV cache)
    through the serving contract. Being a reference implementation it has
    honest limits:

    * No tool calling — ``generate`` returns ``tool_calls=None``.
    * No incremental streaming — ``stream`` yields the completed text as a single
      delta, because the scratch stack decodes eagerly.
    * It needs its own weights: ``weight_path`` (safetensors) and
      ``tokenizer_path`` (tokenizer.json). If either is absent, ``available`` is
      ``False`` and the server reports the model as not loaded.
    """

    def __init__(
        self,
        weight_path: str,
        tokenizer_path: str,
        *,
        n_threads: int = 1,
        n_ctx: int = 2048,
    ) -> None:
        from pathlib import Path

        self.weight_path = Path(weight_path)
        self.tokenizer_path = Path(tokenizer_path)
        self.n_threads = max(1, n_threads)
        self.n_ctx = n_ctx
        self._engine = None  # lazy, like LocalModel

    def _load(self):
        if self._engine is None:
            if not self.available:
                raise FileNotFoundError(
                    f"Scratch engine needs weights at {self.weight_path} and "
                    f"tokenizer at {self.tokenizer_path}."
                )
            from scratch_inference.loader import InferConfig, InferenceEngine

            self._engine = InferenceEngine(
                weight_path=self.weight_path,
                tokenizer_path=self.tokenizer_path,
                config=InferConfig(max_seq=self.n_ctx),
            )
        return self._engine

    @property
    def available(self) -> bool:
        return self.weight_path.is_file() and self.tokenizer_path.is_file()

    def count_tokens(self, text: str) -> int:
        engine = self._load()
        return len(engine.tokenizer.encode_text(text))

    def count_tokens_messages(self, messages: list) -> int:
        return sum(self.count_tokens(m.content or "") for m in messages)

    def generate(
        self,
        messages: list,
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> tuple[str | None, list | None, str]:
        if tools:
            logger.warning("scratch engine ignores tools; serving without them")
        engine = self._load()
        content = engine.generate_chat_text(
            [m.model_dump(exclude_none=True) for m in messages]
            if hasattr(messages[0], "model_dump")
            else [dict(m) for m in messages],
            max_new_tokens=max_tokens,
        )
        return content, None, "stop"

    def stream(
        self,
        messages: list,
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> Iterator[str]:
        content, _calls, _finish = self.generate(messages, max_tokens, tools)
        if content:
            yield content