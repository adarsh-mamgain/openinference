# scheduler

A **priority-queue scheduler library** used inside the
[inference-server](../inference-server/). It is an internal layer between the
HTTP API and the model: the inference-server's chat router submits chat requests
as jobs; a bounded pool of async workers drains the queue in priority-then-FIFO
order, runs the real model, and streams tokens back. It exposes **no HTTP API of
its own** — the inference-server remains the single interface clients talk to.

```
Client → inference-server (POST /v1/chat/completions)
              ↓ scheduler.submit_chat(...)
              PriorityQueue (asyncio min-heap)
              ↓ worker pool (async, bounded)
              inference_server.llm.model (Qwen2.5)
              ↓ result / SSE stream → OpenAI response
```

## What it provides (library API)

```python
from scheduler.scheduler import Scheduler

scheduler = Scheduler(num_workers=2)     # bounded concurrency
await scheduler.start()                  # spawn the worker tasks

# Non-streaming: await completion, read the result
job = await scheduler.submit_chat(messages=[{"role": "user", "content": "hi"}])
await job.done.wait()                    # asyncio.Event set when finished
text = job.result

# Streaming: consume token deltas
job = await scheduler.submit_chat(messages=[...], max_tokens=32, stream=True)
async for delta in scheduler.subscribe_stream(job.id):
    print(delta, end="")

await scheduler.stop()
```

Features:

- **Priority then FIFO** — lower `priority` runs first; equal priorities run in
  arrival order (min-heap with a sequence tiebreaker)
- **Bounded async worker pool** — `NUM_WORKERS` jobs generate concurrently
- **Backpressure** — a bounded queue; `submit_chat` blocks until capacity frees
- **Cancellation** — `cancel(job_id)` removes a still-queued job (lazy-tombstone
  heap removal)
- **Real inference** — workers call `inference_server.llm.model`, including the
  model-driven tool-calling loop and token-level streaming

## Wiring into the inference-server

The inference-server owns the scheduler's life cycle: its FastAPI lifespan calls
`await scheduler.start()` / `await scheduler.stop()`, and its chat router uses
`submit_chat` + `job.done` + `subscribe_stream`. See
`inference-server/src/inference_server/routers/chat.py`.

## Setup (uv workspace)

The monorepo root is a uv workspace containing `inference-server` and
`scheduler`; each depends on the other as a workspace member.

```bash
uv sync --all-packages   # from the repo root
```

## Project layout

```
src/scheduler/
├── __init__.py    # package marker
├── config.py      # worker pool settings (env)
├── schemas.py     # Job = chat request (reuses inference_server Message)
├── store.py       # job registry + bounded history + per-job done Event
├── queue.py       # asyncio min-heap priority queue (FIFO tie-break + cancel)
├── events.py      # stream event bus (token deltas → subscribers)
└── scheduler.py   # the Scheduler class (worker pool + dispatch + library API)
```

## Concepts learned

- **Priority queues / heaps** — `heapq`, lazy-tombstone removal for cancellation
- **Scheduling policies** — priority-then-FIFO, global priority via shared heap
- **Async worker pools** — `asyncio.create_task`, bounded concurrency
- **Backpressure** — bounded queues, blocking `put` under load
- **Streaming / pub-sub** — in-process event bus, `async for` fan-out
- **Monorepo architecture** — an *internal library* (no HTTP surface) consumed
  by a service, sharing schemas across packages
