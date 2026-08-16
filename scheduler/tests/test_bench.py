"""Tests for the benchmark harness (`benchmarks/run.py`)."""

import httpx2 as httpx
import pytest

import scheduler.scheduler as sched_module
from benchmarks import run as bench
from inference_server import main as app_module
from inference_server.routers import chat as chat_module
from scheduler.scheduler import Scheduler


class FakeModel:
    """Slow-ish streamer so TTFT and inter-token latency are measurable."""

    available = True

    def count_tokens(self, text: str) -> int:
        return len(text) // 4 or 1

    def generate(self, messages, max_tokens, tools=None):
        return "done", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        import time as _t

        for tok in ["alpha", " beta", " gamma", " delta"]:
            yield tok
            _t.sleep(0.01)


def _client(bad_key: bool = False) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_module.app),
        base_url="http://test",
        headers={"Authorization": "Bearer dev-key" if not bad_key else "Bearer bad-key"},
    )


@pytest.mark.asyncio
async def test_one_measures_streaming(monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(sched_module, "model", fake)
    monkeypatch.setattr(chat_module, "model", fake)
    private = Scheduler(num_workers=1)
    monkeypatch.setattr(chat_module, "scheduler", private)
    await private.start()

    try:
        async with _client() as client:
            r = await bench._one(client)
            assert "error" not in r
            assert r["latency"] > 0
            assert r["ttft"] is not None and r["ttft"] > 0
            assert r["deltas"] == 4
            assert r["itl"] is not None
    finally:
        await private.stop()


@pytest.mark.asyncio
async def test_one_reports_http_error(monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(sched_module, "model", fake)
    monkeypatch.setattr(chat_module, "model", fake)
    private = Scheduler(num_workers=1)
    monkeypatch.setattr(chat_module, "scheduler", private)
    await private.start()
    try:
        async with _client(bad_key=True) as client:
            r = await bench._one(client)
            assert "error" in r
    finally:
        await private.stop()
