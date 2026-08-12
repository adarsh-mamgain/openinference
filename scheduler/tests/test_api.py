"""End-to-end HTTP tests for the scheduler API (submit / status / list / cancel)."""

import asyncio
import os
import uuid

import httpx2
import pytest

# Configure a fast simulated backend before importing the app.
os.environ.setdefault("SIMULATED_DEFAULT_SECONDS", "0.05")
os.environ.setdefault("NUM_WORKERS", "2")

from scheduler import main as app_module  # noqa: E402
from scheduler.schemas import JobStatus  # noqa: E402

scheduler = app_module.scheduler


@pytest.fixture()
async def client():
    # The module singleton is shared; reset between tests and start the workers.
    await scheduler.start()
    transport = httpx2.ASGITransport(app=app_module.app)
    async with httpx2.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await scheduler.stop()
    # Drop any leftover jobs so tests stay independent.
    scheduler.store._jobs.clear()
    scheduler.store._history.clear()


@pytest.mark.asyncio
async def test_submit_and_poll_completion(client):
    r = await client.post(
        "/v1/jobs",
        json={"payload": {"task": "demo", "seconds": 0.05}, "priority": 0},
    )
    assert r.status_code == 202
    job = r.json()["job"]
    assert job["status"] == JobStatus.QUEUED.value

    # Poll until the job completes.
    final = None
    for _ in range(50):
        s = await client.get(f"/v1/jobs/{job['id']}")
        if s.status_code == 404:
            break  # archived after completion
        final = s.json()["job"]
        if final["status"] in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            break
        await asyncio.sleep(0.02)

    # Once archived the store returns 404 but history has it completed.
    st = await client.get(f"/v1/jobs/{job['id']}")
    assert st.status_code == 404
    listing = (await client.get("/v1/jobs")).json()["data"]
    done = next((j for j in listing if j["id"] == job["id"]), None)
    assert done is not None
    assert done["status"] == JobStatus.COMPLETED.value
    assert "executed demo" in done["result"]


@pytest.mark.asyncio
async def test_cancel_queued_job(client):
    # Slow blocker occupies a worker; a queued job can be cancelled.
    await client.post(
        "/v1/jobs", json={"payload": {"task": "blocker", "seconds": 0.3}, "priority": 0}
    )
    r = await client.post(
        "/v1/jobs", json={"payload": {"task": "victim", "seconds": 0.3}, "priority": 0}
    )
    victim_id = r.json()["job"]["id"]

    await asyncio.sleep(0.1)  # let blocker start, victim stays queued
    cancel = await client.delete(f"/v1/jobs/{victim_id}")
    assert cancel.status_code == 200
    assert cancel.json()["job"]["status"] == JobStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_unknown_job_404(client):
    r = await client.get(f"/v1/jobs/{uuid.uuid4().hex}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["workers"] == 2
