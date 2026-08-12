"""Job data models for the scheduler library.

A job is a *chat completion request* that the scheduler queues by priority and
executes against the inference-server's real local model. ``Message`` is reused
from the inference-server package so request shapes stay identical to the
OpenAI wire format. This is a library, so there are no HTTP response models.
"""

import asyncio
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from inference_server.schemas import Message


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobSubmitRequest(BaseModel):
    messages: list[Message]
    priority: int = Field(default=0, description="Lower value = higher priority")
    model: str = "qwen2.5-0.5b-instruct"
    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    tools: list[dict] | None = None
    stream: bool = Field(default=False, description="Emit token deltas to the subscriber")


class Job(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    priority: int
    messages: list[Message]
    model: str
    max_tokens: int | None
    temperature: float
    tools: list[dict] | None
    stream: bool
    status: JobStatus = JobStatus.QUEUED
    result: str | None = None
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    done: "asyncio.Event" = Field(default_factory=asyncio.Event, exclude=True)
