"""End-to-end HTTP tests for the scheduler API (submit / status / list / cancel /
stream), using a fake model injected into the scheduler module."""

import asyncio
import json
import threading
import uuid

import httpx2
import pytest

import scheduler.scheduler as sched_module
from scheduler import main as app_module
from scheduler.schemas import JobStatus
from scheduler.scheduler import Scheduler


class FakeModel:
    """Instant, controllable model so API tests don't load the real weights."""

    def __init__(self, delay: float = 0.01) -> None:
        self.delay = delay
        self.gates: dict[str, threading.Event] = {}
        self.stream_gates: dict[str, threading.Event] = {}

    def generate(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        gate = self.gates.get(content)
        if gate is not None:
            gate.wait(timeout=self.delay)
        return f"done:{content}", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        yield f"tok1:{content}"
        gate = self.stream_gates.get(content)
        if gate is not None:
            gate.wait(timeout=5)  # hold until the test lets the stream continue
        yield f" tok2:{content}"


@pytest.fixture()
async def client():
    original_model = sched_module.model
    original_scheduler = app_module.scheduler
    fake = FakeModel()
    sched_module.model = fake

    # Use a fresh Scheduler per test so workers/tasks never leak across tests.
    sch: Scheduler = Scheduler()
    app_module.scheduler = sch

    await sch.start()
    transport = httpx2.ASGITransport(app=app_module.app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, fake, sch
    await sch.stop()

    app_module.scheduler = original_scheduler
    sched_module.model = original_model
    # Release any gates from streaming/cancel tests so threads can exit.
    for gate in fake.gates.values():
        gate.set()
    for gate in fake.stream_gates.values():
        gate.set()


def chat_payload(content: str, priority: int = 0, stream: bool = False):
    return {
        "messages": [{"role": "user", "content": content}],
        "priority": priority,
        "stream": stream,
    }


@pytest.mark.asyncio
async def test_submit_and_poll_completion(client):
    c, fake, sch = client
    r = await c.post("/v1/jobs", json=chat_payload("demo"))
    assert r.status_code == 202
    job = r.json()["job"]
    assert job["status"] == JobStatus.QUEUED.value

    await asyncio.sleep(0.1)
    st = await c.get(f"/v1/jobs/{job['id']}")
    assert st.status_code == 404  # archived after completion

    listing = (await c.get("/v1/jobs")).json()["data"]
    done = next((j for j in listing if j["id"] == job["id"]), None)
    assert done is not None
    assert done["status"] == JobStatus.COMPLETED.value
    assert done["result"] == "done:demo"


@pytest.mark.asyncio
async def test_stream_endpoint_emits_deltas(client):
    c, fake, sch = client
    # Hold the fake model's stream open after its first token so the job stays
    # mid-stream (RUNNING) while the SSE endpoint attaches.
    fake.stream_gates["ping"] = threading.Event()
    r = await c.post("/v1/jobs", json=chat_payload("ping", stream=True))
    job_id = r.json()["job"]["id"]

    stream_task = asyncio.create_task(c.get(f"/v1/jobs/{job_id}/stream"))

    # Let the endpoint attach and receive the first delta, then release the rest.
    await asyncio.sleep(0.2)
    fake.stream_gates["ping"].set()

    resp = await asyncio.wait_for(stream_task, timeout=10)
    assert resp.status_code == 200
    events = [l for l in resp.text.splitlines() if l.startswith("data:")]
    assert events[-1] == "data: [DONE]"
    deltas = [
        json.loads(ev[6:])["delta"]
        for ev in events[:-1]
        if ev != "data: [DONE]"
    ]
    assert "".join(deltas) == "tok1:ping tok2:ping"


@pytest.mark.asyncio
async def test_cancel_queued_job(client):
    c, fake, sch = client
    # Block a long first job so the victim stays queued.
    fake.gates["blocker"] = threading.Event()
    await c.post("/v1/jobs", json=chat_payload("blocker"))
    await asyncio.sleep(0.02)
    r = await c.post("/v1/jobs", json=chat_payload("victim"))
    victim_id = r.json()["job"]["id"]

    cancel = await c.delete(f"/v1/jobs/{victim_id}")
    assert cancel.status_code == 200
    assert cancel.json()["job"]["status"] == JobStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_unknown_job_404(client):
    c, _fake, sch = client
    r = await c.get(f"/v1/jobs/{uuid.uuid4().hex}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_health(client):
    c, _fake, sch = client
    r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["workers"] == sch.num_workers
