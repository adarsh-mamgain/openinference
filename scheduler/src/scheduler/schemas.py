"""Job and API data models for the scheduler."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPayload(BaseModel):
    """Arbitrary work to run. Backends interpret this; the simulated backend
    uses `seconds` as an artificial processing delay."""

    task: str = "noop"
    seconds: float | None = Field(default=None, gt=0)
    data: dict[str, Any] = Field(default_factory=dict)


class JobSubmitRequest(BaseModel):
    payload: JobPayload
    priority: int = Field(default=0, description="Lower value = higher priority")


class Job(BaseModel):
    id: str
    priority: int
    payload: JobPayload
    status: JobStatus = JobStatus.QUEUED
    result: str | None = None
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None


class JobStatusResponse(BaseModel):
    job: Job


class JobListResponse(BaseModel):
    object: str = "list"
    data: list[Job]


class HealthResponse(BaseModel):
    status: str = "ok"
    queue_size: int
    in_flight: int
    workers: int
