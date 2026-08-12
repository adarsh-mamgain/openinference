"""Backend abstraction: the thing that actually executes a job.

The scheduler is decoupled from *how* work runs so its core (queue, workers,
priorities) can be studied and tested without a model. To point this at a real
inference model later, implement ``Backend.execute`` on top of the model and
select it via ``SCHEDULER_BACKEND``.
"""

import asyncio
from abc import ABC, abstractmethod

from scheduler.config import settings
from scheduler.schemas import Job


class Backend(ABC):
    """Executes a single submitted job, returning a string result."""

    @abstractmethod
    async def execute(self, job: Job) -> str:
        raise NotImplementedError


class SimulatedBackend(Backend):
    """Pretends to work for a short time, then returns a canned result.

    An artificial delay lets us exercise scheduling mechanics (priorities,
    concurrency, cancellation) without a real model. The delay comes from the
    job payload's ``seconds`` (default from settings).
    """

    async def execute(self, job: Job) -> str:
        delay = job.payload.seconds or settings.simulated_default_seconds
        await asyncio.sleep(delay)
        return f"executed {job.payload.task} after {delay:.2f}s"


def build_backend() -> Backend:
    """Instantiate the backend selected by settings."""
    if settings.backend == "simulated":
        return SimulatedBackend()
    raise ValueError(f"Unknown backend: {settings.backend}")
