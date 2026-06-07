# OpenRouter OSS

A lightweight OpenRouter-style router for open-weight models.

## What is in this repo now

- Public landing page at `/`
- Login page at `/login`
- Signup page at `/signup`
- Customer dashboard at `/app`
- Session-based customer auth
- Unlimited API key creation per workspace
- Credits and usage tracking
- OpenAI-compatible `/v1/chat/completions`
- `/v1/models`, `/v1/me`, `/v1/api-keys`, `/v1/usage/recent`
- Dodo Payments checkout for credit top-ups

## Customer flow

1. Register a workspace.
2. Log in with email and password.
3. Load credits through the dashboard.
4. Create as many API keys as needed.
5. Use the OpenAI SDK against `/v1` with a generated key.

## Run locally

1. Copy `.env.example` to `.env` and fill in provider keys.
2. Install dependencies.
3. Start the app.

```bash
uvicorn app.main:app --reload
```

Open `http://localhost:8000/`.

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

## SDK Example

```python
from openai import OpenAI

client = OpenAI(
    api_key="or_live_xxx",
    base_url="http://localhost:8000/v1",
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)
```
