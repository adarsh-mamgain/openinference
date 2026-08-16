"""Tests for scheduler admission control (reject over capacity)."""

import asyncio
import threading

import httpx2
import pytest

import scheduler.scheduler as sched_module
from inference_server import main as app_module
from inference_server.routers import chat as chat_module
from scheduler.scheduler import Scheduler
from scheduler.schemas import AdmissionRejectedError


class BlockingModel:
    """Gateable model: holds a worker until the gate is released."""

    available = True

    def count_tokens(self, text):
        return len(text) // 4 or 1

    def generate(self, messages, max_tokens, tools=None):
        self.gate.wait(timeout=5)
        return "done", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        yield "tok"


@pytest.fixture()
def blocking_model(monkeypatch):
    model = BlockingModel()
    model.gate = threading.Event()
    monkeypatch.setattr(sched_module, "model", model)
    return model


def _user(content):
    return {"role": "user", "content": content}


@pytest.mark.asyncio
async def test_rejects_when_at_capacity(blocking_model):
    sched = Scheduler(num_workers=1, max_in_flight=1)
    await sched.start()
    try:
        # Hold the single worker with a blocked job.
        first = await sched.submit_chat([_user("hold")], priority=0)
        # Give the worker time to pick it up (now in_flight == 1 == capacity).
        await asyncio.sleep(0.05)
        assert sched.in_flight == 1
        assert not sched.can_admit()

        # A second submit must be rejected.
        with pytest.raises(AdmissionRejectedError):
            await sched.submit_chat([_user("nope")], priority=0)

        blocking_model.gate.set()
        await asyncio.sleep(0.05)
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_admits_when_under_capacity(blocking_model):
    sched = Scheduler(num_workers=2, max_in_flight=4)
    await sched.start()
    try:
        blocking_model.gate.set()  # never block
        assert sched.can_admit()
        for i in range(3):
            await sched.submit_chat([_user(f"ok{i}")], priority=0)
        await asyncio.sleep(0.1)
        # All completed; capacity freed.
        assert sched.can_admit()
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_health_reports_capacity(blocking_model):
    sched = Scheduler(num_workers=1, max_in_flight=3)
    await sched.start()
    try:
        health = sched.health()
        assert health["capacity"] == 3
        assert health["can_admit"] is True
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_chat_returns_503_when_at_capacity(blocking_model, monkeypatch):
    monkeypatch.setattr(chat_module, "model", blocking_model)
    # Private scheduler with capacity 1 injected into the router.
    sched = Scheduler(num_workers=1, max_in_flight=1)
    monkeypatch.setattr(chat_module, "scheduler", sched)
    await sched.start()
    try:
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app_module.app),
            base_url="http://test",
            headers={"Authorization": "Bearer dev-key"},
        ) as c:
            # First request blocks the single worker, filling capacity.
            first = asyncio.create_task(
                c.post(
                    "/v1/chat/completions",
                    json={"messages": [{"role": "user", "content": "a"}]},
                )
            )
            await asyncio.sleep(0.1)
            second = await c.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "b"}]},
            )
            assert second.status_code == 503
            assert "capacity" in second.json()["detail"]

            blocking_model.gate.set()
            first_resp = await first
            assert first_resp.status_code == 200
    finally:
        await sched.stop()
