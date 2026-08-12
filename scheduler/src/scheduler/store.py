"""Job registry holding the live state of every submitted job.

The store is an in-process dict keyed by job id. Because all processing happens
on a single asyncio event loop (workers await rather than hold locks), a plain
dict is safe: no two coroutines mutate the same entry concurrently.
"""

import time
import uuid
from collections import OrderedDict

from scheduler.schemas import Job, JobStatus, JobSubmitRequest


class JobStore:
    def __init__(self, max_history: int = 10_000) -> None:
        self._jobs: dict[str, Job] = {}
        self._history: OrderedDict[str, Job] = OrderedDict()
        self._max_history = max_history

    def create(self, request: JobSubmitRequest) -> Job:
        job = Job(
            id=f"job_{uuid.uuid4().hex[:16]}",
            priority=request.priority,
            messages=request.messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            tools=request.tools,
            stream=request.stream,
            created_at=time.time(),
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def set_status(self, job_id: str, status: JobStatus) -> None:
        job = self._jobs[job_id]
        job.status = status
        now = time.time()
        if status == JobStatus.RUNNING:
            job.started_at = now
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.finished_at = now

    def set_result(self, job_id: str, result: str) -> None:
        self._jobs[job_id].result = result

    def list(self, limit: int = 100) -> list[Job]:
        # Most recently finished first, then queued/running.
        ordered = list(reversed(self._history.values()))
        active = [j for j in self._jobs.values() if j.status in (JobStatus.QUEUED, JobStatus.RUNNING)]
        return (active + ordered)[:limit]

    def archive(self, job: Job) -> None:
        """Move a finished job from the live map into the bounded history."""
        self._jobs.pop(job.id, None)
        self._history[job.id] = job
        self._history.move_to_end(job.id)
        while len(self._history) > self._max_history:
            self._history.popitem(last=False)
