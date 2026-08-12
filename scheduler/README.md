# scheduler

A priority-queue request scheduler for inference workloads, built from scratch
with FastAPI + asyncio. It is the "Scheduler" layer from the inference-server
architecture diagram:

```
Client  →  FastAPI  →  PriorityQueue  →  workers (async)  →  Backend  →  Result
```

Instead of every request hitting the model directly, requests are submitted as
**jobs** into an in-memory priority queue. A bounded pool of async workers
drains the queue, honouring priority (and FIFO among equal priorities), with
bounded concurrency and backpressure.

## What it implements

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health + queue/worker stats |
| `POST /v1/jobs` | Submit a job into the priority queue (202 Accepted) |
| `GET /v1/jobs` | List jobs (active first, then recent history) |
| `GET /v1/jobs/{id}` | Fetch one job's status + result |
| `DELETE /v1/jobs/{id}` | Cancel a queued job |

Features:

- **Priority then FIFO** scheduling — lower `priority` value runs first; equal
  priorities run in arrival order (stable heap with a sequence tiebreaker)
- **Bounded async worker pool** — `NUM_WORKERS` jobs execute concurrently
- **Backpressure** — a max queue size (`MAX_QUEUE_SIZE`); submits block until
  capacity frees up
- **Cancellation** — queued jobs can be cancelled (lazy-tombstone heap removal)
- **Pluggable backend** — the executor is behind a small `Backend` interface; the
  default `SimulatedBackend` applies an artificial delay so the scheduling
  mechanics can be exercised without a model. Swap in a real model later.

## Setup

```bash
uv sync
cp .env.example .env   # optional; defaults are fine for local dev
uv run uvicorn scheduler.main:app --reload
```

Interactive docs: http://localhost:8000/docs

## Try it

```bash
# Submit a job (lower priority number = higher priority)
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"payload":{"task":"summarize","seconds":1.0},"priority":0}'

# Check its status / result
curl http://localhost:8000/v1/jobs/<job_id>

# Submit a lot of jobs and watch higher priorities jump the queue
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"payload":{"task":"low","seconds":10.0},"priority":10}'

# Cancel a queued job
curl -X DELETE http://localhost:8000/v1/jobs/<job_id>

# Health / stats
curl http://localhost:8000/health
```

## Scheduling policy

Jobs are stored in a binary min-heap. Each heap entry compares by
`(priority, seq)`, so:

1. the job with the **lowest `priority`** value is popped first;
2. among equal priorities, the **earlier-submitted** job (lower `seq`) runs
   first — stable FIFO.

Every worker pops from the same heap, so priority is respected globally rather
than per-worker. Because the queue is bounded and workers are bounded, load
above capacity backs up in the queue instead of overwhelming the backend.

## Project layout

```
src/scheduler/
├── main.py        # FastAPI app + endpoints + lifespan
├── config.py      # settings from env
├── schemas.py     # Job / JobStatus / API models
├── store.py       # job registry + bounded history
├── queue.py       # asyncio min-heap priority queue (FIFO tie-break + cancel)
├── backend.py     # pluggable Backend interface + SimulatedBackend
└── scheduler.py   # worker pool + dispatch (the core)
tests/
└── test_scheduler.py
```

## Concepts learned

- **Priority queues / heaps** — `heapq`, lazy-tombstone removal for cancellation
- **Scheduling policies** — priority-then-FIFO, global priority via shared heap
- **Async worker pools** — `asyncio.create_task`, bounded concurrency
- **Backpressure** — bounded queues, blocking `put` under load
- **HTTP API design** — `202 Accepted`, resource lifecycle (create/read/cancel)
