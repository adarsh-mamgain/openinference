"""Tests for the pluggable model engine (Week 3, item 16).

Covers the :class:`ModelEngine` contract, the factory that selects a backend
from ``settings.model_backend``, and the from-scratch adapter (honest: no tools,
single-delta streaming, raises cleanly without weight files).
"""

import pytest

from inference_server.engines import ModelEngine, ScratchEngine
from inference_server.llm import build_model_engine, get_route_model, model
from inference_server.schemas import Message


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