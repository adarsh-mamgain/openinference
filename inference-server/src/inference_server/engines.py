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

import json
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


class ProviderEngine(ModelEngine):
    """Adapter over an OpenAI-compatible ``/chat/completions`` HTTP endpoint.

    This is what makes a ``provider`` route real: the router can delegate a
    request to an external model — another inference-server, or a hosted
    endpoint — instead of only serving local GGUFs. Because the scheduler calls
    ``generate``/``stream`` from a worker thread (``asyncio.to_thread``), the
    HTTP client here is synchronous, exactly like the local engines.

    Honest limits:

    * No local tokenizer — ``count_tokens*`` use a ~4-char-per-token estimate,
      so reported usage is approximate unless the endpoint's own usage field is
      believed instead.
    * Network is assumed reachable when ``base_url`` is configured; availability
      is a static config check, not a reachability probe.
    """

    _HEURISTIC_CHARS_PER_TOKEN = 4

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        transport=None,
    ) -> None:
        import httpx2 as httpx

        self._http = httpx
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._transport = transport
        self._client = None

    def _get_client(self):
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = self._http.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout_seconds,
                transport=self._transport,
            )
        return self._client

    def _payload(self, messages: list, max_tokens: int, tools: list[dict] | None, stream: bool) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                m.model_dump(exclude_none=True)
                if hasattr(m, "model_dump")
                else dict(m)
                for m in messages
            ],
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        return payload

    @property
    def available(self) -> bool:
        return bool(self.base_url)

    def count_tokens(self, text: str) -> int:
        return max(1, round(len(text or "") / self._HEURISTIC_CHARS_PER_TOKEN))

    def count_tokens_messages(self, messages: list) -> int:
        return sum(self.count_tokens(m.content or "") for m in messages) + 4 * len(messages)

    def generate(
        self,
        messages: list,
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> tuple[str | None, list | None, str]:
        response = self._get_client().post(
            "/chat/completions",
            json=self._payload(messages, max_tokens, tools, stream=False),
        )
        response.raise_for_status()
        choice = response.json()["choices"][0]
        message = choice.get("message", {})
        return (
            message.get("content"),
            message.get("tool_calls"),
            choice.get("finish_reason") or "stop",
        )

    def stream(
        self,
        messages: list,
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> Iterator[str]:
        with self._get_client().stream(
            "POST",
            "/chat/completions",
            json=self._payload(messages, max_tokens, tools, stream=True),
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                raw = line[len("data:") :].strip()
                if raw == "[DONE]":
                    break
                delta = json.loads(raw)["choices"][0].get("delta", {})
                text = delta.get("content")
                if text:
                    yield text