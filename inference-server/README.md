# inference-server

An OpenAI-compatible inference API built with FastAPI, from scratch.

Instead of calling OpenAI directly, clients call **this** API and it serves
responses from a real local model — a quantized `Qwen2.5-0.5B-Instruct`
GGUF file running on CPU via llama-cpp-python.

```
Client  →  FastAPI  →  LocalModel (llama.cpp)  →  Streaming Response
```

## What it implements

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /v1/chat/completions` | Chat completions (OpenAI format) |
| `POST /v1/embeddings` | Embeddings (OpenAI format) |

Features:

- Real local model inference (`Qwen2.5-0.5B-Instruct` Q4_K_M, ~470MB)
- Streaming chat completions via SSE (Server-Sent Events)
- Bearer API-key authentication
- In-memory fixed-window rate limiting
- Tool / function calling (`get_weather`, `add`)

## Setup

```bash
uv sync

# Download the model (~470MB) once
./scripts/download-model.sh

cp .env.example .env   # optional; defaults are fine for local dev
uv run uvicorn inference_server.main:app --reload
```

Interactive docs: http://localhost:8000/docs

> Model binaries are gitignored. Fresh clones must run
> `scripts/download-model.sh` first. Set `MODEL_BACKEND=mock` to use the
> deterministic echo fallback instead of the local model.

## Try it

```bash
# Non-streaming chat
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-0.5b-instruct","messages":[{"role":"user","content":"Explain what an API is in one sentence."}]}'

# Streaming chat
curl -N http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-0.5b-instruct","messages":[{"role":"user","content":"Say hello in 3 words."}],"stream":true}'

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
├── llm.py           # LocalModel wrapper around llama-cpp-python
├── mock_model.py    # echo fallback + tool registry
└── routers/
    ├── chat.py          # POST /v1/chat/completions
    └── embeddings.py    # POST /v1/embeddings
```

## Concepts learned

- **HTTP + FastAPI** — request/response modeling, dependency injection
- **Streaming** — SSE wire format, async generators
- **Async programming** — `async def`, `asyncio.to_thread` for blocking
  CPU-bound inference, why `StopIteration` breaks across thread boundaries
- **Local inference** — GGUF quantization, llama-cpp, CPU threading
- **OpenAI API design** — request/response shapes that clients expect
- **Production API concerns** — auth, rate limiting, tool calling
