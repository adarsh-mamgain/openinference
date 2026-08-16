"""Tests for the metrics registry and the `/metrics` endpoint."""

import json

import httpx2
import pytest

import scheduler.scheduler as sched_module
from inference_server import main as app_module
from inference_server.metrics import Metrics, _percentile
from inference_server.routers import chat as chat_module
from scheduler.scheduler import Scheduler


class FakeModel:
    """Instant model with a fixed stream length so TTFT/ITL are observable."""

    def __init__(self) -> None:
        self.available = True

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def generate(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        return f"done:{content}", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        for tok in ["one", " two", " three"]:
            yield tok


# --------------------------------------------------------------------------- #
# Pure-unit tests for the registry helpers
# --------------------------------------------------------------------------- #


def test_percentile():
    samples = sorted([1.0, 2.0, 3.0, 4.0])
    assert _percentile(samples, 50) == 2.5
    assert _percentile(samples, 0) == 1.0
    assert _percentile(samples, 100) == 4.0
    assert _percentile([], 50) is None


def test_metrics_aggregates_and_counts():
    m = Metrics()
    m.record_request(200)
    m.record_request(200)
    m.record_request(503)
    m.record_latency(0.01)
    m.record_latency(0.02)
    m.record_ttft(0.05)
    m.record_inter_token(0.03)
    m.record_tokens(10, 5)

    s = m.summary()
    assert s["requests"]["total"] == 3
    assert s["requests"]["errors"] == 1
    assert s["requests"]["by_status"]["2xx"] == 2
    assert s["requests"]["by_status"]["5xx"] == 1
    assert s["latency_ms"]["count"] == 2
    assert s["ttft_ms"]["count"] == 1
    assert s["inter_token_latency_ms"]["count"] == 1
    assert s["tokens"] == {"prompt": 10, "completion": 5, "total": 15}


# --------------------------------------------------------------------------- #
# Endpoint test: streaming chat populates TTFT/inter-token, /metrics readable
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_streaming_records_ttft_and_metrics_endpoint(monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(sched_module, "model", fake)
    monkeypatch.setattr(chat_module, "model", fake)

    # Use a private Scheduler injected into the router so this test is fully
    # isolated from the global singleton (which other tests also start/stop).
    private = Scheduler(num_workers=1)
    monkeypatch.setattr(chat_module, "scheduler", private)
    await private.start()

    from inference_server.metrics import metrics
    metrics.reset()

    try:
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app_module.app),
            base_url="http://test",
        ) as c:
            r = await c.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer dev-key"},
                json={"messages": [{"role": "user", "content": "ping"}], "stream": True},
            )
            assert r.status_code == 200
            events = [l for l in r.text.splitlines() if l.startswith("data:")]
            assert events[-1] == "data: [DONE]"
            assert any(
                json.loads(ev[6:])["choices"][0]["delta"].get("content")
                for ev in events[:-1]
            )

            mr = await c.get("/metrics")
            assert mr.status_code == 200
            body = mr.json()
            assert body["ttft_ms"]["count"] == 1
            assert body["inter_token_latency_ms"]["count"] == 2
            assert body["requests"]["total"] >= 1
    finally:
        await private.stop()
