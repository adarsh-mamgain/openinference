"""Tests for the scheduler core (priority, FIFO, concurrency, cancel, lifecycle)."""

import asyncio

import pytest

from scheduler.backend import Backend
from scheduler.schemas import Job, JobPayload, JobStatus
from scheduler.scheduler import Scheduler


def payload(task: str) -> JobPayload:
    return JobPayload(task=task, seconds=0.01)


class GatedBackend(Backend):
    """Records the order in which jobs start executing, then blocks until
    released, so tests can assert on deterministic scheduling order."""

    def __init__(self) -> None:
        self.start_order: list[str] = []  # job ids in the order execution started
        self.gates: dict[str, asyncio.Event] = {}
        self.started = asyncio.Event()

    async def execute(self, job: Job) -> str:
        self.start_order.append(job.id)
        if job.id not in self.gates:
            self.gates[job.id] = asyncio.Event()
        self.started.set()
        await self.gates[job.id].wait()
        return f"done:{job.id}"


async def wait_until(predicate, timeout: float = 3.0) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.005)
    return False


async def release_all(backend: GatedBackend) -> None:
    for gate in backend.gates.values():
        gate.set()


async def auto_release(backend: GatedBackend):
    """Release each job's gate right after it starts, so a single worker can
    move on to the next job (order is already recorded before release)."""
    while True:
        for gate in backend.gates.values():
            gate.set()
        await asyncio.sleep(0.005)


@pytest.mark.asyncio
async def test_priority_schedules_highest_first():
    """With one worker, jobs start in priority order: lowest number first."""
    backend = GatedBackend()
    sched = Scheduler(num_workers=1, backend=backend)
    await sched.start()
    try:
        low = await sched.submit(payload("low"), priority=10)
        high = await sched.submit(payload("high"), priority=0)
        medium = await sched.submit(payload("medium"), priority=5)

        releaser = asyncio.create_task(auto_release(backend))
        await wait_until(lambda: len(backend.start_order) == 3)
        releaser.cancel()

        assert backend.start_order == [high.id, medium.id, low.id]
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_fifo_among_equal_priorities():
    """Equal priorities start in submission (FIFO) order."""
    backend = GatedBackend()
    # Enough workers that all three can start; start order is still queue order.
    sched = Scheduler(num_workers=3, backend=backend)
    await sched.start()
    try:
        a = await sched.submit(payload("a"), priority=0)
        b = await sched.submit(payload("b"), priority=0)
        c = await sched.submit(payload("c"), priority=0)

        await wait_until(lambda: len(backend.start_order) == 3)
        assert backend.start_order == [a.id, b.id, c.id]

        await release_all(backend)
        await wait_until(lambda: sched.queue_size == 0)
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_job_completes_and_is_recorded():
    backend = GatedBackend()
    sched = Scheduler(num_workers=1, backend=backend)
    await sched.start()
    try:
        job = await sched.submit(payload("x"), priority=0)
        await wait_until(lambda: job.id in backend.gates)
        backend.gates[job.id].set()

        # Job is archived (removed from the live store) once finished.
        await wait_until(lambda: sched.store.get(job.id) is None)
        history = sched.store.list()
        finished = next((j for j in history if j.id == job.id), None)
        assert finished is not None
        assert finished.status == JobStatus.COMPLETED
        assert finished.result == f"done:{job.id}"
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_cancel_queued_job():
    backend = GatedBackend()
    sched = Scheduler(num_workers=1, backend=backend)
    await sched.start()
    try:
        first = await sched.submit(payload("blocker"), priority=0)
        second = await sched.submit(payload("victim"), priority=0)

        # first starts (occupies the single worker); second stays queued.
        await wait_until(lambda: first.id in backend.gates)
        assert second.id not in backend.gates  # still queued

        cancelled = await sched.cancel(second.id)
        assert cancelled is not None
        assert cancelled.status == JobStatus.CANCELLED

        backend.gates[first.id].set()
        await wait_until(lambda: sched.queue_size == 0)
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_backpressure_blocks_when_full():
    backend = GatedBackend()
    # maxsize 1 => only one job may occupy the queue.
    sched = Scheduler(num_workers=0, max_queue_size=1, backend=backend)
    await sched.start()
    try:
        first = await sched.submit(payload("one"), priority=0)
        assert sched.queue_size == 1

        second_task = asyncio.create_task(sched.submit(payload("two"), priority=0))
        await asyncio.sleep(0.1)
        assert second_task.done() is False  # blocked by backpressure

        # Free capacity, the blocked submit proceeds.
        await sched.cancel(first.id)
        second = await asyncio.wait_for(second_task, timeout=1.0)
        assert second is not None
    finally:
        await sched.stop()


@pytest.mark.asyncio
async def test_bounded_concurrency():
    backend = GatedBackend()
    sched = Scheduler(num_workers=2, backend=backend)
    await sched.start()
    try:
        jobs = [await sched.submit(payload(f"j{i}"), priority=0) for i in range(5)]

        # Exactly num_workers jobs start; the rest remain queued.
        await wait_until(lambda: len(backend.start_order) == 2)
        assert backend.start_order == [jobs[0].id, jobs[1].id]
        assert sched.queue_size == 3

        await release_all(backend)
        await wait_until(lambda: sched.queue_size == 0)
    finally:
        await sched.stop()
