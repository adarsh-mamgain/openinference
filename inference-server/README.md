# inference-server

An OpenAI-compatible inference API built with FastAPI, from scratch.

Instead of calling OpenAI directly, clients call **this** API and it serves
responses from real local models running on CPU via llama-cpp-python:

* **Chat completions** — `Qwen2.5-0.5B-Instruct` (Q4_K_M, ~490MB)
* **Embeddings** — `nomic-embed-text-v1.5` (Q8_0, ~146MB)

```
Client  →  FastAPI  →  llama.cpp  →  Streaming Response
```

## What it implements

| Endpoint | Description |
|----------|-------------|
| `GET /` | Landing page (single CTA → `/docs`) |
| `GET /health` | Health check |
| `POST /v1/chat/completions` | Chat completions (OpenAI format) |
| `POST /v1/embeddings` | Embeddings (OpenAI format) |
| `GET /v1/models` | List served models |

Features:

- Real local model inference, token-for-token streaming via SSE
- **Real tokenizer** for `usage` accounting (no heuristics)
- **Model-driven tool / function calling** (`get_weather`, `add`) — the model
  decides when to call a tool, the tool is executed, and the model reasons over
  the result
- Real semantic embeddings from a dedicated local embedding model
- Bearer API-key authentication
- In-memory fixed-window rate limiting

## Setup

```bash
uv sync

# Download both GGUF models (total ~640MB) once
./scripts/download-model.sh

cp .env.example .env   # optional; defaults are fine for local dev
uv run uvicorn inference_server.main:app --reload
```

Interactive docs: http://localhost:8000/docs
Landing page: http://localhost:8000/

> Model binaries are gitignored. Fresh clones must run
> `scripts/download-model.sh` first. There is no mock/echo fallback — if a
> model file is missing, the corresponding endpoint returns a clear 503.

## Deploy to Coolify (Nixpacks)

The repo ships a `nixpacks.toml` so Coolify's Nixpacks builder builds and runs
the app without a Dockerfile:

1. **Add a resource** → **Public Repository** → point at this repo
   (`inference-server/` directory).
2. **Build Pack**: `Nixpacks`.
3. Add env vars under **Environment Variables**:
   - `API_KEY` — your real key (do not use the `dev-key` default)
   - `CHAT_MODEL_PATH=models/qwen2.5-0.5b-instruct-q4_k_m.gguf`
   - `EMBEDDING_MODEL_PATH=models/nomic-embed-text-v1.5.Q8_0.gguf`
   - `MODEL_CTX=512` and `MODEL_THREADS=2` are sane defaults for a shared
     4-core box — tune if you have headroom.
4. Deploy. The build downloads both GGUF weights into the image, then starts
   `uvicorn` on `$PORT` (Coolify sets this).

**How the build works** (`nixpacks.toml`):

- `setup` — Python 3.11 (from `.python-version`) + `curl`
- `install` — `uv sync --no-dev --frozen`, which installs the prebuilt
  `llama-cpp-python` CPU wheel pinned in `uv.lock` (no source compilation, so
  builds are fast and don't need a huge toolchain)
- `build` — `scripts/download-model.sh` bakes both models into the image
- `start` — `uvicorn inference_server.main:app --host 0.0.0.0 --port ${PORT:-8000}`

Notes:

- The whole build is CPU-only; it needs no GPU.
- On a 7.5GB box, ~640MB of model weights + 512-token contexts leaves plenty
  of headroom. `MODEL_THREADS=2` keeps llama.cpp from hogging all cores.
- Health check: `/health` (Coolify can use it for the readiness probe).

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

# Tool / function calling (model decides to call get_weather)
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-0.5b-instruct","messages":[{"role":"user","content":"What is the weather in london?"}]}'

# Embeddings
curl http://localhost:8000/v1/embeddings \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed-text-v1.5","input":["hello","world"]}'

# List models
curl http://localhost:8000/v1/models -H "Authorization: Bearer dev-key"
```

## Project layout

```
src/inference_server/
├── main.py          # FastAPI app + route wiring + landing page
├── landing.py       # HTML landing page for `/`
├── config.py        # settings from env
├── auth.py          # Bearer API-key dependency
├── rate_limit.py    # fixed-window rate limiter
├── exceptions.py    # app-specific HTTP exceptions
├── schemas.py       # OpenAI-compatible Pydantic models
├── llm.py           # LocalModel + EmbeddingModel wrappers (llama-cpp)
├── tools.py         # tool schemas + handlers + Qwen text-tool parser
└── routers/
    ├── chat.py          # POST /v1/chat/completions
    ├── embeddings.py    # POST /v1/embeddings
    └── models.py        # GET /v1/models
scripts/
└── download-model.sh # fetches both GGUF weights
nixpacks.toml         # Coolify / Nixpacks build config
```

## How tool calling works

OpenAI-style APIs let the user declare `tools` and let the *model* decide to
call them. This server does that with a real model:

1. The registered tools (`get_weather`, `add`) are passed to llama.cpp via the
   OpenAI `tools` param.
2. Larger instruct models return structured `tool_calls`; the small
   Qwen2.5-0.5B renders its call as the chat-template text
   (`<tool_call>{"name": ...}`), which we parse.
3. The tool is executed by its handler and the JSON result is fed back into
   the conversation as a `role: tool` message.
4. The model answers based on the result (bounded by a turn budget).

## Concepts learned

- **HTTP + FastAPI** — request/response modeling, dependency injection
- **Streaming** — SSE wire format, async generators
- **Async programming** — `async def`, `asyncio.to_thread` for blocking
  CPU-bound inference, and why `StopIteration` breaks across thread boundaries
- **Local inference** — GGUF quantization, llama-cpp, CPU threading
- **Embeddings** — dedicated embedding models, vector shape, tokenizer reuse
- **Tool calling** — model-driven function selection, JSON arguments, result
  round-tripping; chat-template text formats on small models
- **OpenAI API design** — request/response shapes clients expect
- **Production API concerns** — auth, rate limiting, ready-to-serve landing
