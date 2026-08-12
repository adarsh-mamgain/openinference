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
