# inference-server

An OpenAI-compatible inference API built with FastAPI, from scratch.

Instead of calling OpenAI directly, clients call **this** API and it serves
responses from a pluggable model backend (here a mock model).

```
Client  →  FastAPI  →  mock model  →  Streaming Response
```

## What it implements

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /v1/chat/completions` | Chat completions (OpenAI format) |
| `POST /v1/embeddings` | Embeddings (OpenAI format) |

Features:

- Streaming chat completions via SSE (Server-Sent Events)
- Bearer API-key authentication
- In-memory fixed-window rate limiting
- Tool / function calling (`get_weather`, `add`)

## Run it

```bash
uv sync
cp .env.example .env   # optional; defaults are fine for local dev
uv run uvicorn inference_server.main:app --reload
```

Interactive docs: http://localhost:8000/docs

## Try it

```bash
# Non-streaming chat
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-model","messages":[{"role":"user","content":"hello"}]}'

# Streaming chat
curl -N http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-model","messages":[{"role":"user","content":"hello"}],"stream":true}'

# Tool calling
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"weather in london"}],"tools":[{"type":"function","function":{"name":"get_weather","parameters":{"type":"object","properties":{"location":{"type":"string"}},"required":["location"]}}}]}'

# Embeddings
curl http://localhost:8000/v1/embeddings \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-embedding","input":["hello","world"]}'
```

## Project layout

```
src/inference_server/
├── main.py          # FastAPI app + route wiring
├── config.py        # settings from env
├── auth.py          # Bearer API-key dependency
├── rate_limit.py    # fixed-window rate limiter
├── schemas.py       # OpenAI-compatible Pydantic models
├── mock_model.py    # mock LLM backend + tool registry
└── routers/
    ├── chat.py          # POST /v1/chat/completions
    └── embeddings.py    # POST /v1/embeddings
```

## Concepts learned

- **HTTP + FastAPI** — request/response modeling, dependency injection
- **Streaming** — SSE wire format, async generators
- **Async programming** — `async def`, `asyncio.sleep`, streaming responses
- **OpenAI API design** — request/response shapes that clients expect
- **Production API concerns** — auth, rate limiting, tool calling
