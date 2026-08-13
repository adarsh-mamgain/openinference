"""Integration test: inference-server HTTP chat routes through the scheduler.

Validates the full chain HTTP endpoint -> scheduler queue/worker -> model for
both non-streaming and streaming chat completions, using a fake model injected
into the scheduler module.
"""

import asyncio
import json
import threading

import httpx2
import pytest

import scheduler.scheduler as sched_module
from inference_server import main as app_module
from inference_server.routers import chat as chat_module
from scheduler.scheduler import scheduler as global_scheduler


class FakeModel:
    """Instant model; streaming can be gated to keep the job mid-stream."""

    def __init__(self, delay: float = 0.01) -> None:
        self.delay = delay
        self.gates: dict[str, threading.Event] = {}
        self.stream_gates: dict[str, threading.Event] = {}
        self.available = True

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def generate(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        gate = self.gates.get(content)
        if gate is not None:
            gate.wait(timeout=self.delay)
        return f"done:{content}", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        yield f"tok1:{content}"
        gate = self.stream_gates.get(content)
        if gate is not None:
            gate.wait(timeout=5)
        yield f" tok2:{content}"


@pytest.mark.asyncio
async def test_chat_routes_through_scheduler():
    original = {
        "sched": sched_module.model,
        "chat": chat_module.model,
    }
    fake = FakeModel()
    sched_module.model = fake
    chat_module.model = fake

    await global_scheduler.start()
    transport = httpx2.ASGITransport(app=app_module.app)
    try:
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
            await _test_non_streaming(c, fake)
            await _test_streaming(c, fake)
    finally:
        await global_scheduler.stop()
        sched_module.model = original["sched"]
        chat_module.model = original["chat"]


async def _test_non_streaming(c, fake):
    r = await c.post(
        "/v1/chat/completions",
        headers=_headers(),
        json={"messages": [{"role": "user", "content": "demo"}]},
    )
    assert r.status_code == 200
    body = r.json()
    content = body["choices"][0]["message"]["content"]
    assert content == "done:demo"
    assert body["usage"]["completion_tokens"] >= 1


async def _test_streaming(c, fake):
    # Hold the stream open after its first token so the job stays mid-stream
    # while the SSE endpoint attaches.
    fake.stream_gates["ping"] = threading.Event()
    stream_task = asyncio.create_task(
        c.post(
            "/v1/chat/completions",
            headers=_headers(),
            json={
                "messages": [{"role": "user", "content": "ping"}],
                "stream": True,
            },
        )
    )
    await asyncio.sleep(0.3)
    fake.stream_gates["ping"].set()

    resp = await asyncio.wait_for(stream_task, timeout=10)
    assert resp.status_code == 200
    events = [l for l in resp.text.splitlines() if l.startswith("data:")]
    assert events[-1] == "data: [DONE]"
    deltas = []
    for ev in events[:-1]:
        if ev == "data: [DONE]":
            continue
        delta = json.loads(ev[6:])["choices"][0]["delta"].get("content")
        if delta:
            deltas.append(delta)
    assert "".join(deltas) == "tok1:ping tok2:ping"


def _headers():
    return {"Authorization": "Bearer dev-key"}
