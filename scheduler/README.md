# scheduler

A priority-queue request scheduler that fronts the **inference-server's real
local model**. Part of the `openinference` monorepo (uv workspace). Instead of
every request hitting the model directly, clients submit chat-completion
**jobs** into an in-memory priority queue; a bounded pool of async workers
drains the queue in priority-then-FIFO order, runs the model, and streams
tokens back.

```
Client → FastAPI (POST /v1/jobs) → PriorityQueue → workers (async)
        → inference_server.llm.model (Qwen2.5) → result / SSE stream
```

## What it implements

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health + queue/worker stats |
| `POST /v1/jobs` | Submit a chat-completion job into the priority queue (202) |
| `GET /v1/jobs` | List jobs (active first, then history) |
| `GET /v1/jobs/{id}` | Fetch one job's status + result |
| `GET /v1/jobs/{id}/stream` | SSE stream of token deltas for a streaming job |
| `DELETE /v1/jobs/{id}` | Cancel a queued job |

Features:

- **Priority then FIFO** scheduling — lower `priority` value runs first; equal
  priorities run in arrival order (min-heap with a sequence tiebreaker)
- **Bounded async worker pool** — `NUM_WORKERS` jobs generate concurrently
- **Backpressure** — a bounded queue; submits block until capacity frees up
- **Cancellation** — queued jobs can be cancelled (lazy-tombstone heap removal)
- **Real inference** — jobs run against `inference_server.llm.model`
- **Streaming** — token deltas are fanned out over an in-process event bus to
  the SSE endpoint

## Setup (uv workspace)

The monorepo root is a uv workspace containing `inference-server` and
`scheduler`, so the scheduler depends on the real model directly.

```bash
uv sync --all-packages   # from the repo root; installs both packages
```

Run the scheduler (point the model at the GGUF weights):

```bash
cd scheduler
cp .env.example .env
uv run uvicorn scheduler.main:app --reload
```

Interactive docs: http://localhost:8000/docs

## Try it

```bash
# Submit a chat job (lower priority number = higher priority)
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Explain an API in one sentence."}],"priority":0}'

# Submit a streaming job, then watch token deltas
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Count 1 2 3."}],"stream":true}'
curl -N http://localhost:8000/v1/jobs/<job_id>/stream

# Status / result (archived jobs return 404 and appear in /v1/jobs history)
curl http://localhost:8000/v1/jobs/<job_id>

# Cancel a queued job
curl -X DELETE http://localhost:8000/v1/jobs/<job_id>

# Queue stats
curl http://localhost:8000/health
```

## Scheduling policy

Jobs live in a binary min-heap keyed by `(priority, seq)`, so:

1. the job with the **lowest `priority`** runs first;
2. among equal priorities, the **earlier-submitted** job (lower `seq`) runs
   first — stable FIFO.

Every worker pops from the same heap, so priority is respected globally rather
than per-worker. Bounded workers + a bounded queue mean load above capacity
backs up instead of overwhelming the model.

## Project layout

```
src/scheduler/
├── main.py        # FastAPI app + endpoints + streaming SSE
├── config.py      # settings from env
├── schemas.py     # job = chat request (reuses inference_server Message)
├── store.py       # job registry + bounded history
├── queue.py       # asyncio min-heap priority queue (FIFO tie-break + cancel)
├── events.py      # stream event bus (token deltas → SSE subscribers)
└── scheduler.py   # worker pool + dispatch, calls inference_server.llm.model
```

## Concepts learned

- **Priority queues / heaps** — `heapq`, lazy-tombstone removal for cancellation
- **Scheduling policies** — priority-then-FIFO, global priority via shared heap
- **Async worker pools** — `asyncio.create_task`, bounded concurrency
- **Backpressure** — bounded queues, blocking `put` under load
- **Streaming / pub-sub** — in-process event bus, SSE fan-out to subscribers
- **Monorepo integration** — uv workspace, cross-package import of the model
