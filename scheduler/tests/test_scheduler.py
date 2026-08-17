"""Tests for the scheduler core (priority, FIFO, concurrency, backpressure,
cancel, completion, streaming) as a library.

Inference is exercised through a fake model injected into the scheduler module,
so tests are deterministic and don't load llama-cpp or touch the real weights.
"""

import asyncio
import threading
import time

import pytest

import scheduler.scheduler as sched_module
from scheduler.events import END
from scheduler.scheduler import Scheduler


class FakeModel:
    """Minics inference_server.llm.model with configurable timing and gating."""

    def __init__(self, delay: float = 0.01) -> None:
        self.delay = delay
        self.start_order: list[str] = []
        self._active = 0
        self._max_active = 0
        self.gates: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def generate(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        with self._lock:
            self._active += 1
            self._max_active = max(self._max_active, self._active)
            self.start_order.append(content)
        gate = self.gates.setdefault(content, threading.Event())
        gate.wait(timeout=self.delay)  # releases immediately if already set
        with self._lock:
            self._active -= 1
        return f"done:{content}", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        yield f"hi {content}"
        time.sleep(0.05)
        yield f" bye {content}"


@pytest.fixture()
def fake_model_factory():
    original = sched_module.model
    made: list[FakeModel] = []

    def factory(**kw):
        fake = FakeModel(**kw)
        made.append(fake)
        sched_module.model = fake
        return fake

    yield factory
    sched_module.model = original
    for fake in made:
        for gate in fake.gates.values():
            gate.set()


def user(content: str):
    return {"role": "user", "content": content}


@pytest.mark.asyncio
async def test_priority_schedules_highest_first(fake_model_factory):
    fake = fake_model_factory()
    sched = Scheduler(num_workers=1)
    await sched.start()
    try:
        await sched.submit_chat([user("low")], priority=10)
        await sched.submit_chat([user("high")], priority=0)
        await sched.submit_chat([user("medium")], priority=5)

        await asyncio.sleep(0.1)
        assert fake.start_order == ["high", "medium", "low"]
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_fifo_among_equal_priorities(fake_model_factory):
    fake = fake_model_factory()
    sched = Scheduler(num_workers=1)
    await sched.start()
    try:
        for i in range(3):
            await sched.submit_chat([user(f"m{i}")], priority=0)

        await asyncio.sleep(0.1)
        assert fake.start_order == ["m0", "m1", "m2"]
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_bounded_concurrency(fake_model_factory):
    fake = fake_model_factory(delay=0.2)
    sched = Scheduler(num_workers=2, max_in_flight=10)
    await sched.start()
    try:
        jobs = [await sched.submit_chat([user(f"j{i}")], priority=0) for i in range(5)]

        await asyncio.sleep(0.8)
        assert fake._max_active == 2
        # All five eventually complete.
        completed = [j for j in jobs if j.status.value == "completed"]
        assert len(completed) == 5
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_job_completes_and_is_recorded(fake_model_factory):
    fake = fake_model_factory()
    sched = Scheduler(num_workers=1)
    await sched.start()
    try:
        job = await sched.submit_chat([user("x")])

        await job.done.wait()
        assert job.status.value == "completed"
        assert job.result == "done:x"
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_cancel_queued_job(fake_model_factory):
    fake = fake_model_factory()
    sched = Scheduler(num_workers=1)
    await sched.start()
    try:
        # Gate the blocker so it holds the single worker; the victim stays queued.
        fake.gates["blocker"] = threading.Event()
        await sched.submit_chat([user("blocker")], priority=0)
        await asyncio.sleep(0.02)
        victim = await sched.submit_chat([user("victim")], priority=0)

        cancelled = await sched.cancel(victim.id)
        assert cancelled is not None
        assert cancelled.status.value == "cancelled"

        # Release the blocker so shutdown is clean.
        fake.gates["blocker"].set()
        await asyncio.sleep(0.02)
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_cannot_cancel_running_job(fake_model_factory):
    fake = fake_model_factory()
    sched = Scheduler(num_workers=1)
    await sched.start()
    try:
        fake.gates["running"] = threading.Event()  # block it in-flight
        running = await sched.submit_chat([user("running")], priority=0)
        await asyncio.sleep(0.02)

        assert await sched.cancel(running.id) is None  # running, not cancellable

        fake.gates["running"].set()
        await asyncio.sleep(0.02)
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_backpressure_blocks_until_capacity_frees(fake_model_factory):
    fake = fake_model_factory()
    sched = Scheduler(num_workers=0, max_queue_size=1)
    await sched.start()
    try:
        first = await sched.submit_chat([user("one")], priority=0)
        assert sched.queue_size == 1

        second_task = asyncio.create_task(sched.submit_chat([user("two")], priority=0))
        await asyncio.sleep(0.05)
        assert second_task.done() is False  # blocked by backpressure

        # Free capacity; the blocked submit proceeds.
        await sched.cancel(first.id)
        await asyncio.wait_for(second_task, timeout=1.0)
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_streaming_publishes_deltas(fake_model_factory):
    fake = fake_model_factory()
    sched = Scheduler(num_workers=1)
    await sched.start()
    try:
        job = await sched.submit_chat([user("ping")], priority=0, stream=True)

        deltas = []
        async for delta in sched.subscribe_stream(job.id):
            deltas.append(delta)
        assert deltas == ["hi ping", " bye ping"]
        await job.done.wait()
        assert job.result == "hi ping bye ping"
    finally:
        await sched.stop()


# --------------------------------------------------------------------------- #
# Failure modes (Week 4, item 18)
# --------------------------------------------------------------------------- #


class _HangingModel:
    """Model whose generate never returns — used to prove timeouts."""

    available = True

    def generate(self, messages, max_tokens, tools=None):
        threading.Event().wait(timeout=1.0)
        return "never", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        threading.Event().wait(timeout=1.0)
        yield "never"


@pytest.mark.asyncio
async def test_job_times_out_instead_of_hanging(fake_model_factory, monkeypatch):
    """A hung generation must fail the job, not wedge a worker forever."""
    fake = _HangingModel()
    monkeypatch.setattr(sched_module, "model", fake)
    sched = Scheduler(num_workers=1, job_timeout_seconds=0.2)
    await sched.start()
    try:
        job = await sched.submit_chat([user("stuck")], priority=0)

        await asyncio.wait_for(job.done.wait(), timeout=5.0)
        assert job.status.value == "failed"
        assert "timed out" in job.result
        # The worker is free again: a fast job still goes through.
        await sched.submit_chat([user("x")])
        await asyncio.sleep(0.05)
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_streaming_job_times_out_and_subscriber_releases(fake_model_factory, monkeypatch):
    """A stalled stream must end for its subscriber, not hang the SSE reader."""
    fake = _HangingModel()
    monkeypatch.setattr(sched_module, "model", fake)
    sched = Scheduler(num_workers=1, job_timeout_seconds=0.2)
    await sched.start()
    try:
        job = await sched.submit_chat([user("stuck")], priority=0, stream=True)

        collected = []
        async for delta in sched.subscribe_stream(job.id):
            collected.append(delta)
        assert collected == []  # stream ended via timeout, no deltas
        await job.done.wait()
        assert job.status.value == "failed"
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_stop_drains_in_flight_then_cancels(fake_model_factory):
    """stop() waits for in-flight jobs (grace) before cancelling stragglers."""
    fake = fake_model_factory(delay=0.3)  # each generate takes 300ms
    sched = Scheduler(num_workers=1, shutdown_grace_seconds=2.0)
    await sched.start()
    job = await sched.submit_chat([user("slow")], priority=0)

    await asyncio.sleep(0.05)  # let the worker pick it up
    await sched.stop()  # should wait for the 300ms job to finish

    assert job.status.value == "completed"
    assert job.result == "done:slow"


@pytest.mark.asyncio
async def test_stop_closes_open_streams(fake_model_factory, monkeypatch):
    """Streams left open at shutdown must release subscribers, not hang them."""
    fake = _HangingModel()
    monkeypatch.setattr(sched_module, "model", fake)
    sched = Scheduler(num_workers=1, job_timeout_seconds=30.0)
    await sched.start()
    job = await sched.submit_chat([user("stuck")], priority=0, stream=True)
    await asyncio.sleep(0.05)

    await sched.stop()  # must close the open stream

    collected = []
    async for delta in sched.subscribe_stream(job.id):
        collected.append(delta)
    assert collected == []
