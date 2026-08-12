"""FastAPI application for the scheduler.

Exposes an HTTP surface for submitting chat-completion jobs into the priority
queue, checking their status, listing, cancelling queued jobs, and streaming
token deltas from a running streaming job as SSE.
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse

from scheduler.config import settings
from scheduler.events import END
from scheduler.schemas import (
    HealthResponse,
    Job,
    JobListResponse,
    JobStatus,
    JobStatusResponse,
    JobSubmitRequest,
)
from scheduler.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(**scheduler.health())


@app.post("/v1/jobs", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(request: JobSubmitRequest) -> JobStatusResponse:
    """Enqueue a chat-completion job. Returns 202 Accepted with the job."""
    job = scheduler.store.create(request)
    await scheduler.submit(job)
    return JobStatusResponse(job=job)


@app.get("/v1/jobs", response_model=JobListResponse)
def list_jobs() -> JobListResponse:
    return JobListResponse(data=scheduler.store.list())


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str) -> JobStatusResponse:
    job = _get_scheduler_job(job_id)
    return JobStatusResponse(job=job)


@app.delete("/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def cancel_job(job_id: str) -> JobStatusResponse:
    """Cancel a queued job. In-flight jobs cannot be aborted."""
    job = _get_scheduler_job(job_id)
    cancelled = await scheduler.cancel(job.id)
    if cancelled is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is running or already finished and cannot be cancelled",
        )
    return JobStatusResponse(job=cancelled)


@app.get("/v1/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    """Stream token deltas from a running streaming job as SSE."""
    job = _get_scheduler_job(job_id)
    if not job.stream:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job was not submitted with stream=true",
        )

    async def event_generator():
        # Wait for the job's stream to be created by its worker (or finish).
        queue = None
        for _ in range(200):  # ~5s budget to reach RUNNING and create the stream
            queue = scheduler.bus.stream_or_none(job_id)
            if queue is not None:
                break
            finished = scheduler.store.get(job_id)
            if finished is None or finished.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                break
            await asyncio.sleep(0.025)

        if queue is None:
            yield _sse({"finish_reason": "done"})
            yield "data: [DONE]\n\n"
            return

        ended = False
        while True:
            item = await queue.get()
            if item is END:
                ended = True
                break
            yield _sse({"delta": item})

        if not ended:
            yield _sse({"finish_reason": "done"})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _get_scheduler_job(job_id: str) -> Job:
    job = scheduler.store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    return job


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
