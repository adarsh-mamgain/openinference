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

- Real local model inference (`Qwen2.5-0.5B-Instruct` Q4_K_M, ~490MB)
- Streaming chat completions via SSE (Server-Sent Events)
- Bearer API-key authentication
- In-memory fixed-window rate limiting
- Tool / function calling (`get_weather`, `add`)

## Setup

```bash
uv sync

# Download the model (~490MB) once
./scripts/download-model.sh

cp .env.example .env   # optional; defaults are fine for local dev
uv run uvicorn inference_server.main:app --reload
```

Interactive docs: http://localhost:8000/docs

> Model binaries are gitignored. Fresh clones must run
> `scripts/download-model.sh` first. Set `MODEL_BACKEND=mock` to use the
> deterministic echo fallback instead of the local model.

## Deploy to Coolify (Nixpacks)

The repo ships a `nixpacks.toml` so Coolify's Nixpacks builder builds and runs
the app without a Dockerfile:

1. **Add a resource** → **Public Repository** → point at this repo
   (`inference-server/` directory).
2. **Build Pack**: `Nixpacks`.
3. Add env vars under **Environment Variables**:
   - `API_KEY` — your real key (do not use the `dev-key` default)
   - `MODEL_BACKEND=local`
   - `MODEL_PATH=models/qwen2.5-0.5b-instruct-q4_k_m.gguf`
   - `MODEL_CTX=512` and `MODEL_THREADS=2` are sane defaults for a shared
     4-core box — tune if you have headroom.
4. Deploy. The build downloads the ~490MB GGUF into the image, then starts
   `uvicorn` on `$PORT` (Coolify sets this).

**How the build works** (`nixpacks.toml`):

- `setup` — Python 3.11 (from `.python-version`) + `curl`
- `install` — `uv sync --no-dev --frozen`, which installs the prebuilt
  `llama-cpp-python` CPU wheel pinned in `uv.lock` (no source compilation, so
  builds are fast and don't need a huge toolchain)
- `build` — `scripts/download-model.sh` bakes the model into the image
- `start` — `uvicorn inference_server.main:app --host 0.0.0.0 --port ${PORT:-8000}`

Notes:

- The whole build is CPU-only; it needs no GPU.
- On a 7.5GB box shared with other apps, ~490MB of model weights + a 512-token
  context leaves plenty of headroom. `MODEL_THREADS=2` keeps llama.cpp from
  hogging all cores.
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
scripts/
└── download-model.sh # fetches the GGUF weights
nixpacks.toml         # Coolify / Nixpacks build config
```

## Concepts learned

- **HTTP + FastAPI** — request/response modeling, dependency injection
- **Streaming** — SSE wire format, async generators
- **Async programming** — `async def`, `asyncio.to_thread` for blocking
  CPU-bound inference, why `StopIteration` breaks across thread boundaries
- **Local inference** — GGUF quantization, llama-cpp, CPU threading
- **OpenAI API design** — request/response shapes that clients expect
- **Production API concerns** — auth, rate limiting, tool calling
