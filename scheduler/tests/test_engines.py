"""Tests for the pluggable model engine (Week 3, item 16).

Covers the :class:`ModelEngine` contract, the factory that selects a backend
from ``settings.model_backend``, and the from-scratch adapter (honest: no tools,
single-delta streaming, raises cleanly without weight files).
"""

import asyncio
import json

import httpx2
import pytest

from inference_server.config import settings as cfg
from inference_server.engines import ModelEngine, ProviderEngine, ScratchEngine
from inference_server.llm import build_model_engine, get_route_model, model
from inference_server.router.models import RouteBackend
from inference_server.router.registry import build_routes, provider_route
from inference_server.schemas import Message
from scheduler.scheduler import Scheduler


def _fake_inference_engine(monkeypatch, text: str = "hello from scratch"):
    """Patch scratch_inference.loader.InferenceEngine with a toy impl."""
    import types

    class _FakeInferenceEngine:
        def __init__(self, *args, **kwargs):
            self.tokenizer = types.SimpleNamespace(
                encode_text=lambda s: list(range(len(s))),
            )

        def generate_chat_text(self, messages, max_new_tokens, **kwargs):
            return text

    import scratch_inference.loader as scratch_loader

    monkeypatch.setattr(scratch_loader, "InferenceEngine", _FakeInferenceEngine)
    return _FakeInferenceEngine


# --------------------------------------------------------------------------- #
# Interface conformance
# --------------------------------------------------------------------------- #


def test_model_is_modelengine():
    assert isinstance(model, ModelEngine)


def test_engine_contract_methods_exist():
    for name in ("available", "count_tokens", "count_tokens_messages", "generate", "stream"):
        assert hasattr(model, name), f"default model missing {name}"
    assert callable(model.count_tokens)
    assert callable(model.generate)
    assert callable(model.stream)


def test_scratch_implements_contract():
    engine = ScratchEngine("x.safetensors", "y.json")
    for name in ("available", "count_tokens", "count_tokens_messages", "generate", "stream"):
        assert hasattr(engine, name), f"scratch engine missing {name}"


# --------------------------------------------------------------------------- #
# Factory selection
# --------------------------------------------------------------------------- #


def test_factory_local_backend(monkeypatch):
    from inference_server.config import settings as orig

    monkeypatch.setattr(orig, "model_backend", "local", raising=False)
    built = build_model_engine()
    assert type(built).__name__ == "LocalModel"
    assert isinstance(built, ModelEngine)


def test_factory_scratch_backend(monkeypatch):
    from inference_server.config import settings as cfg

    monkeypatch.setattr(cfg, "model_backend", "scratch", raising=False)
    built = build_model_engine()
    assert isinstance(built, ScratchEngine)


def test_route_model_returns_engine(tmp_path, monkeypatch):
    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"fake")
    patched_model = _FakeModelPatched()

    import inference_server.llm as llm

    monkeypatch.setattr(llm, "_route_models", {})
    monkeypatch.setattr(llm, "model", patched_model)

    # A path that is not the configured default -> fresh cached LocalModel-ish.
    engine = get_route_model(str(gguf))
    assert engine is not patched_model
    assert engine.available  # path exists -> thin wrapper reports available
    # The exact configured path -> the default model instance.
    assert get_route_model(llm.settings.model_path) is patched_model


class _FakeModelPatched:
    available = True


# --------------------------------------------------------------------------- #
# Scratch adapter behavior
# --------------------------------------------------------------------------- #


def test_scratch_unavailable_without_files(tmp_path):
    engine = ScratchEngine(str(tmp_path / "no.safetensors"), str(tmp_path / "no.json"))
    assert not engine.available
    with pytest.raises(FileNotFoundError):
        engine.count_tokens("hi")


def test_scratch_generate_ignores_tools_and_returns_text(tmp_path, monkeypatch):
    _fake_inference_engine(monkeypatch, text="42")
    w = tmp_path / "m.safetensors"
    t = tmp_path / "tok.json"
    w.write_bytes(b"x")
    t.write_bytes(b"{}")

    engine = ScratchEngine(str(w), str(t))
    content, calls, finish = engine.generate(
        [Message(role="user", content="2+2?")], max_tokens=8, tools=[{"type": "function"}]
    )
    assert content == "42"
    assert calls is None
    assert finish == "stop"


def test_scratch_stream_single_delta(tmp_path, monkeypatch):
    _fake_inference_engine(monkeypatch, text="hello")
    w = tmp_path / "m.safetensors"
    t = tmp_path / "tok.json"
    w.write_bytes(b"x")
    t.write_bytes(b"{}")

    engine = ScratchEngine(str(w), str(t))
    deltas = list(engine.stream([Message(role="user", content="hi")], max_tokens=4))
    assert deltas == ["hello"]


def test_scratch_count_tokens_uses_tokenizer(tmp_path, monkeypatch):
    _fake_inference_engine(monkeypatch)
    w = tmp_path / "m.safetensors"
    t = tmp_path / "tok.json"
    w.write_bytes(b"x")
    t.write_bytes(b"{}")

    engine = ScratchEngine(str(w), str(t))
    assert engine.count_tokens("abc") == 3  # fake encode: len(text)


# --------------------------------------------------------------------------- #
# Provider engine (OpenAI-compatible HTTP backend)
# --------------------------------------------------------------------------- #


def _provider_handler(content="42", tool_calls=None, auth_header=None):
    """Build an httpx2.MockTransport handler that speaks the OpenAI wire format."""

    def handler(request):
        if auth_header is not None:
            assert request.headers.get("authorization") == auth_header
        body = json.loads(request.read())
        if body.get("stream"):
            chunks = [
                {"choices": [{"delta": {"content": tok}, "finish_reason": None}]}
                for tok in ["hel", "lo"]
            ]
            sse = "".join("data: {}\n\n".format(json.dumps(c)) for c in chunks)
            sse += "data: [DONE]\n\n"
            return httpx2.Response(
                200, text=sse, headers={"content-type": "text/event-stream"}
            )
        return httpx2.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": content, "tool_calls": tool_calls},
                        "finish_reason": "tool_calls" if tool_calls else "stop",
                    }
                ]
            },
        )

    return handler


def test_provider_implements_contract():
    engine = ProviderEngine("http://provider.test")
    for name in ("available", "count_tokens", "count_tokens_messages", "generate", "stream"):
        assert hasattr(engine, name), f"provider engine missing {name}"
    assert isinstance(engine, ModelEngine)


def test_provider_available_reflects_url():
    assert ProviderEngine("http://provider.test").available
    assert not ProviderEngine("").available
    assert not ProviderEngine("  ").available


def test_provider_generate_returns_content_and_tool_calls():
    engine = ProviderEngine(
        "http://provider.test",
        model="cloud",
        transport=httpx2.MockTransport(
            _provider_handler(content=None, tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "add", "arguments": "{}"}}])
        ),
    )
    content, calls, finish = engine.generate(
        [Message(role="user", content="2+2?")], max_tokens=16, tools=[{"type": "function"}]
    )
    assert content is None
    assert calls[0]["function"]["name"] == "add"
    assert finish == "tool_calls"


def test_provider_stream_yields_deltas():
    engine = ProviderEngine(
        "http://provider.test",
        transport=httpx2.MockTransport(_provider_handler()),
    )
    assert list(engine.stream([Message(role="user", content="hi")], max_tokens=16)) == ["hel", "lo"]


def test_provider_sends_bearer_token():
    engine = ProviderEngine(
        "http://provider.test",
        api_key="sekrit",
        transport=httpx2.MockTransport(_provider_handler(auth_header="Bearer sekrit")),
    )
    content, _calls, finish = engine.generate([Message(role="user", content="hi")], max_tokens=4)
    assert content == "42"
    assert finish == "stop"


def test_provider_count_tokens_is_heuristic():
    engine = ProviderEngine("http://provider.test")
    assert engine.count_tokens("abcd") == 1  # ~4 chars per token
    assert engine.count_tokens("") == 1
    assert engine.count_tokens_messages([Message(role="user", content="abcd")]) >= 4


def test_provider_route_registered_from_settings(monkeypatch):
    assert provider_route() is None  # unset -> no provider route

    monkeypatch.setattr(cfg, "provider_url", "http://provider.test", raising=False)
    monkeypatch.setattr(cfg, "provider_model", "remote-qwen", raising=False)
    monkeypatch.setattr(cfg, "provider_identifier", "cloud-qwen", raising=False)
    route = provider_route()
    assert route is not None
    assert route.backend == RouteBackend.PROVIDER
    assert route.provider_url == "http://provider.test"
    assert route.model_identifier == "remote-qwen"  # remote model id on the wire
    assert route.available()

    routes = build_routes(available_check=lambda: model.available)
    ids = {r.id: r.backend for r in routes}
    assert ids.get("cloud-qwen") == RouteBackend.PROVIDER
    monkeypatch.setattr(cfg, "provider_url", None, raising=False)


@pytest.mark.asyncio
async def test_provider_engine_serves_scheduler_job():
    """A provider route registered on the scheduler executes end-to-end."""
    engine = ProviderEngine(
        "http://provider.test",
        model="cloud",
        transport=httpx2.MockTransport(_provider_handler(content="42")),
    )
    sched = Scheduler(num_workers=1)
    sched.register_model("cloud-qwen", engine)
    await sched.start()
    try:
        job = await sched.submit_chat(
            [{"role": "user", "content": "2+2?"}],
            model_name="cloud-qwen",
            max_tokens=16,
        )
        await asyncio.wait_for(job.done.wait(), timeout=10)
        assert job.status.value == "completed"
        assert job.result == "42"
    finally:
        await sched.stop()