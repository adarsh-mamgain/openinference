"""The scheduler: a bounded pool of async workers draining a priority queue.

Work flows::

    submit() -> store.create() -> queue.put(QueueItem)
        worker loop: queue.get() -> mark running -> backend.execute() -> archive

Priority is honoured because every worker pops from the same min-heap, so the
highest-priority outstanding job is always picked next regardless of which
worker is free. Concurrency is bounded by ``num_workers``.
"""

import asyncio
import logging

from scheduler.backend import Backend
from scheduler.config import settings
from scheduler.queue import PriorityQueue, QueueItem
from scheduler.schemas import Job, JobPayload, JobStatus
from scheduler.store import JobStore

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        num_workers: int = settings.num_workers,
        max_queue_size: int = settings.max_queue_size,
        backend: Backend | None = None,
    ) -> None:
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.backend = backend or _default_backend()
        self.store = JobStore()
        self.queue = PriorityQueue(maxsize=self.max_queue_size)
        self.in_flight = 0
        self._seq = 0
        self._workers: list[asyncio.Task] = []

    async def start(self) -> None:
        """Spawn the worker tasks. Idempotent."""
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(self._worker(i), name=f"worker-{i}")
            for i in range(self.num_workers)
        ]

    async def stop(self) -> None:
        """Cancel all workers and wait for them to finish."""
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

    async def submit(self, payload: JobPayload, priority: int = 0) -> Job:
        """Create and enqueue a job. Blocks under backpressure until space frees."""
        job = self.store.create(payload, priority)
        seq = self._seq
        self._seq += 1
        await self.queue.put(QueueItem(priority=priority, seq=seq, job_id=job.id))
        return job

    async def cancel(self, job_id: str) -> Job | None:
        """Cancel a job if it is still queued. In-flight jobs cannot be aborted.

        Returns the cancelled :class:`Job`, or ``None`` if the job wasn't queued
        (e.g. already running or finished).
        """
        if await self.queue.cancel(job_id):
            job = self.store.get(job_id)
            if job is not None:
                self.store.set_status(job_id, JobStatus.CANCELLED)
                self.store.archive(job)
                return job
        return None

    async def _worker(self, index: int) -> None:
        """Process jobs from the priority queue until cancelled."""
        logger.info("worker %d started", index)
        try:
            while True:
                item = await self.queue.get()
                job = self.store.get(item.job_id)
                if job is None or _is_terminal(job.status):
                    continue
                await self._run(job)
        except asyncio.CancelledError:
            logger.info("worker %d stopped", index)
            raise

    async def _run(self, job: Job) -> None:
        self.in_flight += 1
        self.store.set_status(job.id, JobStatus.RUNNING)
        try:
            await asyncio.sleep(settings.worker_poll_seconds)
            result = await self.backend.execute(job)
            self.store.set_result(job.id, result)
            self.store.set_status(job.id, JobStatus.COMPLETED)
        except Exception as exc:  # noqa: BLE001 - surface per-job failures
            logger.exception("job %s failed", job.id)
            self.store.set_result(job.id, f"error: {exc}")
            self.store.set_status(job.id, JobStatus.FAILED)
        finally:
            self.in_flight -= 1
            self.store.archive(job)

    @property
    def queue_size(self) -> int:
        return self.queue.qsize()

    def health(self) -> dict:
        return {
            "status": "ok",
            "queue_size": self.queue_size,
            "in_flight": self.in_flight,
            "workers": self.num_workers,
        }

    async def __aenter__(self) -> "Scheduler":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()


def _is_terminal(status: JobStatus) -> bool:
    return status in (
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    )


def _default_backend() -> Backend:
    from scheduler.backend import build_backend

    return build_backend()


# Module-level singleton shared across requests.
scheduler = Scheduler()
