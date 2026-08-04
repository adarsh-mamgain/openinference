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
- [ ] 2. Set up `uv` project (pyproject.toml, deps, .gitignore)
- [ ] 3. Basic FastAPI app with health check
- [ ] 4. `POST /v1/chat/completions` (non-streaming)
- [ ] 5. `POST /v1/embeddings`
- [ ] 6. Streaming chat completions (SSE)
- [ ] 7. Authentication (API key)
- [ ] 8. Rate limiting
- [ ] 9. Tool calling / function calling

## Upcoming Projects

- [ ] scheduler
- [ ] kv-cache
- [ ] gpu-autoscaler
- [ ] benchmark-suite
- [ ] rag-system
- [ ] vector-db
- [ ] tokenizer
- [ ] distributed-serving
- [ ] monitoring
- [ ] blogs/
