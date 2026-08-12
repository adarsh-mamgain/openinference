# AI Infrastructure Portfolio — Roadmap

Hands-on projects to learn AI infrastructure engineering. Each project is
built step-by-step, kept intentionally simple, and committed one change at a time.

## Project 1 — OpenAI-Compatible Inference API ⭐⭐⭐⭐⭐

The foundation. Users call our API instead of OpenAI; we forward to (or mock) a
model behind the scenes.

**Architecture**

```
User
  ↓
FastAPI
  ↓
Scheduler
  ↓
Tokenizer
  ↓
Model
  ↓
Streaming Response
```

**What we learn**

- HTTP
- Streaming (SSE)
- Async programming
- OpenAI API design
- Production API concerns (auth, rate limiting, tools)

**Steps**

- [x] 1. Create `todo.md`, `README.md`, `LICENSE.md`
- [x] 2. Set up `uv` project (pyproject.toml, deps, .gitignore)
- [x] 3. Basic FastAPI app with health check
- [x] 4. `POST /v1/chat/completions` (non-streaming)
- [x] 5. `POST /v1/embeddings`
- [x] 6. Streaming chat completions (SSE)
- [x] 7. Authentication (API key)
- [x] 8. Rate limiting
- [x] 9. Tool calling / function calling
- [x] 10. Serve real local model (Qwen2.5-0.5B GGUF via llama-cpp-python)
- [x] 11. Landing page at `/` with a single CTA to `/docs`
- [x] 12. Remove mock backend — real tokenizer token counting
- [x] 13. Model-driven tool calling with the real local model (incl. Qwen
       chat-template text format parsing)
- [x] 14. Real embeddings via a dedicated local model (nomic-embed-text)
- [x] 15. `GET /v1/models` listing the served models

## Project 2 — Priority-Queue Scheduler ⭐⭐⭐⭐

The "Scheduler" layer between clients and the model. Requests enter a priority
queue and a bounded pool of async workers drain it in priority-then-FIFO order,
with bounded concurrency and backpressure. It now runs real inference against
the inference-server's local model via a uv workspace.

**Architecture**

```
Client
  ↓
FastAPI (submit / status / cancel / stream)
  ↓
PriorityQueue (asyncio min-heap)
  ↓
Worker Pool (async, bounded)
  ↓
inference_server.llm.model → Result / SSE stream
```

**What we learn**

- Priority queues / heaps (`heapq`, lazy-tombstone cancel)
- Scheduling policies (priority-then-FIFO)
- Async worker pools & bounded concurrency
- Backpressure (bounded queue, blocking put)
- Streaming / pub-sub (event bus → SSE)
- Monorepo integration (uv workspace, cross-package import of the model)

**Steps**

- [x] 1. Scaffold `scheduler/` uv project (pyproject, README, .gitignore)
- [x] 2. Job model + status schemas
- [x] 3. In-memory priority queue (FIFO tie-break, cancellation)
- [x] 4. Async worker pool with bounded concurrency
- [x] 5. Backpressure (max queue size, blocking put)
- [x] 6. Pluggable `Backend` + simulated executor
- [x] 7. FastAPI endpoints (submit / list / status / cancel, health)
- [x] 8. Tests (priority, FIFO, concurrency, backpressure, cancel, API)
- [x] 9. Docs (README, root README, roadmap)
- [x] 10. Integrate with inference-server (uv workspace; drop Backend/mock;
       worker calls `inference_server.llm.model`)
- [x] 11. Streaming jobs (event bus + `GET /v1/jobs/{id}/stream` SSE)

## Upcoming Projects

- [ ] kv-cache
- [ ] gpu-autoscaler
- [ ] benchmark-suite
- [ ] rag-system
- [ ] vector-db
- [ ] tokenizer
- [ ] distributed-serving
- [ ] monitoring
- [ ] blogs/
