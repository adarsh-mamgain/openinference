"""FastAPI application for the scheduler.

Exposes an HTTP surface for submitting jobs into the priority queue,
checking their status, listing, and cancelling queued jobs.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from scheduler.config import settings
from scheduler.schemas import (
    HealthResponse,
    JobListResponse,
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
    """Enqueue a job. Returns 202 Accepted with the job immediately."""
    job = await scheduler.submit(request.payload, request.priority)
    return JobStatusResponse(job=job)


@app.get("/v1/jobs", response_model=JobListResponse)
def list_jobs() -> JobListResponse:
    return JobListResponse(data=scheduler.store.list())


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str) -> JobStatusResponse:
    job = scheduler.store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    return JobStatusResponse(job=job)


@app.delete("/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def cancel_job(job_id: str) -> JobStatusResponse:
    """Cancel a queued job. In-flight jobs cannot be aborted."""
    job = scheduler.store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    cancelled = await scheduler.cancel(job_id)
    if cancelled is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is running or already finished and cannot be cancelled",
        )
    return JobStatusResponse(job=cancelled)
