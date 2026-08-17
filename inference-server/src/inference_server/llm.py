"""Local model backends powered by llama-cpp-python.

Two real models are loaded lazily on first use (so the server can boot even
before weights are downloaded):

* ``LocalModel`` — a chat/instruct GGUF (Qwen2.5-0.5B-Instruct) used for chat
  completions, token-level streaming, tool calling, and token counting via the
  real tokenizer.
* ``EmbeddingModel`` — a dedicated embedding GGUF (nomic-embed-text) used for
  ``/v1/embeddings``.

Although the models load lazily for a forgiving boot experience, there is no
mock or echo fallback: if a model file is missing the endpoints surface a
clear error telling the operator to run ``scripts/download-model.sh``.
"""

from pathlib import Path
from typing import Iterator

from inference_server.config import settings
from inference_server.exceptions import ModelUnavailableError
from inference_server.schemas import FunctionCall, Message, ToolCall


def _require(path: str) -> "Path":
    p = Path(path)
    if not p.is_file():
        raise ModelUnavailableError(
            f"Model file not found at {p}. Run `scripts/download-model.sh` to fetch it."
        )
    return p


class LocalModel:
    """Thin wrapper around a llama-cpp Llama instance serving chat."""

    def __init__(self, model_path: str, n_ctx: int, n_threads: int) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._llm = None

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama

            _require(self.model_path)
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
        """Return the exact token count using the real tokenizer."""
        llm = self._load()
        return len(llm.tokenize(text.encode("utf-8")))

    def count_tokens_messages(self, messages: list[Message]) -> int:
        """Approximate prompt tokens as the sum of the message token counts."""
        return sum(self.count_tokens(m.content or "") for m in messages)

    def generate(
        self,
        messages: list[Message],
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> tuple[str | None, list[ToolCall] | None, str]:
        """Run a chat completion.

        Returns ``(content, tool_calls, finish_reason)``. When the model emits a
        tool call, ``content`` will be ``None`` and ``tool_calls`` populated.
        """
        llm = self._load()

        payload: dict = {
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        result = llm.create_chat_completion(**payload)
        choice = result["choices"][0]
        message = choice["message"]

        tool_calls = None
        raw_calls = message.get("tool_calls")
        if raw_calls:
            tool_calls = [
                ToolCall(
                    id=call["id"],
                    function=FunctionCall(
                        name=call["function"]["name"],
                        arguments=call["function"]["arguments"],
                    ),
                )
                for call in raw_calls
            ]
        return message.get("content"), tool_calls, choice.get("finish_reason", "stop")

    def stream(
        self,
        messages: list[Message],
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> Iterator[str]:
        """Yield text deltas as the model generates them."""
        llm = self._load()

        payload: dict = {
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        stream = llm.create_chat_completion(**payload)
        for chunk in stream:
            choice = chunk["choices"][0]
            delta = choice.get("delta", {})
            text = delta.get("content", "")
            if text:
                yield text


class EmbeddingModel:
    """Wrapper around a llama-cpp Llama instance loaded for embeddings."""

    def __init__(self, model_path: str, n_ctx: int, n_threads: int) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._llm = None

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama

            _require(self.model_path)
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                embedding=True,
                verbose=False,
            )
        return self._llm

    @property
    def available(self) -> bool:
        return Path(self.model_path).is_file()

    def count_tokens(self, text: str) -> int:
        """Return the exact token count using the embedding model's tokenizer."""
        llm = self._load()
        return len(llm.tokenize(text.encode("utf-8")))

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning normalized vectors."""
        llm = self._load()
        result = llm.create_embedding(texts)
        return [item["embedding"] for item in result["data"]]


# Module-level singletons shared across requests.
model = LocalModel(
    model_path=settings.model_path,
    n_ctx=settings.model_ctx,
    n_threads=settings.model_threads,
)

embedding_model = EmbeddingModel(
    model_path=settings.embedding_model_path,
    n_ctx=settings.embedding_model_ctx,
    n_threads=settings.model_threads,
)



# Cached LocalModel instances for additional local routes (e.g. quantized
# siblings served by the router). Each is keyed by its GGUF path so the same
# file is never loaded twice. Instances are created lazily (weights load on
# first use), so registering routes at boot is cheap.
_route_models: dict[str, LocalModel] = {}


def get_route_model(model_path: str) -> LocalModel:
    """Return a cached LocalModel for a route's GGUF, or the default model."""
    if model_path == settings.model_path:
        return model
    if model_path not in _route_models:
        _route_models[model_path] = LocalModel(
            model_path=model_path,
            n_ctx=settings.model_ctx,
            n_threads=settings.model_threads,
        )
    return _route_models[model_path]

def use_real_model() -> bool:
    """Whether the local chat model file is present and should be used."""
    return settings.model_backend == "local" and model.available
