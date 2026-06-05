# OpenRouter OSS MVP - Self-Hosted Open Source Models Router

## Project Overview

**Goal**: Build a lightweight, cost-effective alternative to OpenRouter focused **only on open-weight models**.

- Target: Support up to 100 active users averaging 10M tokens/day (1B tokens total/day)
- Business: 1-5% markup as middleman + value-added features
- Core: OpenAI-compatible API proxy with intelligent routing

**Key Features for MVP**:
- OpenAI-compatible endpoint (`/v1/chat/completions`, etc.)
- Routing to multiple open-source providers (cheapest/fastest/reliable)
- Caching (Redis)
- Usage tracking & billing (DodoPayments)
- Rate limiting & user budgets
- Logging & basic analytics
- Focus on top OSS models: Llama, Qwen, DeepSeek, Mistral, Gemma

**Non-goals for MVP**: Full self-hosted GPU cluster, advanced ML routing, fine-tuning service.

---

## Tech Stack (Cheapest + Reliable)

- **Router/Proxy**: [LiteLLM](https://github.com/BerriAI/litellm) (core)
- **Language**: Python
- **Cache**: Redis
- **Database**: PostgreSQL (for users, usage logs)
- **Billing**: DodoPayments
- **Deployment**: Docker + Docker Compose (later Kubernetes)
- **Hosting**: Hetzner / DigitalOcean / Railway (cheap)
- **Providers**: DeepInfra, Together.ai, Fireworks.ai, DeepSeek API, Groq

---

## Project Structure

```
openrouter-oss/
├── app/
│   ├── main.py                 # FastAPI entrypoint
│   ├── litellm_proxy.py        # LiteLLM config & custom router
│   ├── middleware/
│   │   ├── auth.py
│   │   ├── billing.py
│   │   └── caching.py
│   ├── models/
│   ├── routes/
│   └── utils/
├── config/
│   ├── litellm_config.yaml     # Model mappings & providers
│   ├── providers.json
│   └── settings.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── migrations/                 # For DB
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Step-by-Step Implementation Guide

### 1. Setup Environment

```bash
mkdir openrouter-oss && cd openrouter-oss
python -m venv venv
source venv/bin/activate

pip install litellm fastapi uvicorn redis psycopg2-binary dodopayments[aiohttp] python-dotenv
```

### 2. LiteLLM Configuration (`config/litellm_config.yaml`)

```yaml
model_list:
  - model_name: llama-4-scout
    litellm_params:
      model: together_ai/meta-llama/Llama-4-Scout-109B
      api_key: os.environ[Together_API_KEY]

  - model_name: deepseek-v4-flash
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ[DeepSeek_API_KEY]

  - model_name: qwen3-32b
    litellm_params:
      model: fireworks_ai/accounts/fireworks/models/qwen3-32b
      api_key: os.environ[Fireworks_API_KEY]

  # Add more: Groq for speed, DeepInfra for cheap, etc.

general_settings:
  completion_model: deepseek-v4-flash  # Default fallback
```

### 3. Main Application (`app/main.py`)

```python
from fastapi import FastAPI
from litellm import Router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="OSS Router")

# Initialize LiteLLM Router
router = Router(
    model_list=...,  # load from yaml
    redis_host=os.getenv("REDIS_HOST"),
    redis_port=6379,
    # caching, fallbacks, etc.
)

@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    # Add auth, billing check middleware here
    response = await router.acompletion(**request)
    # Log usage, charge user
    return response

# Health check, models list, etc.
```

### 4. User Authentication & Billing (`app/middleware/`)

Implement simple API key auth + DodoPayments customer + credit system.

Key tables:
- `users` (api_key, credits, plan)
- `usage_logs` (user_id, tokens_in, tokens_out, model, cost)

### 5. Caching Strategy

Use LiteLLM's built-in Redis cache + semantic cache for similar prompts.

### 6. Provider Keys Setup

Get API keys from:
- Together.ai
- Fireworks.ai
- DeepInfra
- DeepSeek
- Groq

Store securely in `.env`

---

## Deployment

### Docker Compose (`docker/docker-compose.yml`)

```yaml
services:
  redis:
    image: redis:alpine
    ports: ["6379:6379"]

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: oss_router
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data

  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [redis, postgres]
```

Run: `docker compose up -d`

### Cloud Deployment Options (Cheapest)

1. **Railway / Render** - Easiest (one-click)
2. **Hetzner Cloud** - Cheapest VPS (~$10-20/month for starter)
3. **Fly.io** - Good for global low latency

---

## Pricing & Model Strategy (MVP)

**Sell at**:
- `$0.25 - $0.80 / million tokens` (depending on model speed/quality)
- Example:
  - DeepSeek V4 Flash: Buy ~$0.20 → Sell $0.25
  - Llama 4 Scout: Buy ~$0.40 → Sell $0.48

**Target Users**:
- Indie hackers building AI agents
- Small startups needing cheap RAG/coding tools
- Developers wanting open-source sovereignty

---

## Roadmap After MVP

1. Advanced routing logic (cost + latency + quality score)
2. Self-hosted vLLM instances on RunPod/Vast.ai for hot models
3. Analytics dashboard
4. Fine-tuning LoRA hosting
5. Enterprise features (SLA, private instances)

---

## Important Notes

- Start small: Validate with 10-20 users first
- Monitor token costs daily
- Implement strong rate limiting
- Be transparent about which providers you route to
- Add fallback logic to prevent downtime

## Next Steps

1. Clone this structure
2. Get API keys from 3 providers
3. Deploy LiteLLM proxy first (even without custom code)
4. Test with `curl` or OpenAI Python client
5. Add auth + billing layer

Good luck! This MVP can be built in **1-2 weeks**.
```

---

**File Created Successfully**: `openrouter_oss_mvp.md`
