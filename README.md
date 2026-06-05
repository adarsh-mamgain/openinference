# OpenRouter OSS

Lightweight self-hosted router for open-weight models.

## What is in this repo now

- Public landing page at `/`
- Login page at `/login`
- Signup page at `/signup`
- Customer dashboard at `/app`
- LiteLLM config loader
- OpenAI-compatible `/v1/chat/completions` entrypoint
- `/health`, `/v1/models`, `/v1/me`, and `/v1/usage/recent`
- Docker Compose for app, Redis, and Postgres
- Dodo Payments client wrapper for checkout/billing flows

## Run locally

1. Copy `.env.example` to `.env` and fill in provider keys.
2. Install dependencies.
3. Start the app with Uvicorn.

```bash
uvicorn app.main:app --reload
```

Then open `http://localhost:8000/`.

## Payments

This project uses Dodo Payments instead of Stripe.

Install the SDK:

```bash
pip install dodopayments
```

For enhanced async performance with aiohttp:

```bash
pip install dodopayments[aiohttp]
```

## Customer UI

The UI is split into three surfaces:

- landing page for prospective customers
- login/signup flow for workspace access
- inner app dashboard for usage, billing, models, and the API console

The dashboard uses the same backend APIs the product exposes to customers.
