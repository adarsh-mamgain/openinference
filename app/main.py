from __future__ import annotations

from datetime import timezone
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.control_plane import CONTROL_PLANE
from app.litellm_proxy import list_model_names, load_litellm_config, proxy_chat_completion
from app.middleware.auth import require_api_key
from app.models import (
    AccountResponse,
    ChatCompletionRequest,
    HealthResponse,
    ModelInfo,
    UsageItemResponse,
    UsageResponse,
)
from app.services.auth import AuthenticationError
from app.settings import SETTINGS
from app.ui import render_app_page, render_landing_page, render_login_page, render_signup_page


app = FastAPI(title=SETTINGS.app_name)


def get_current_user(api_key: str = Depends(require_api_key)):
    try:
        return CONTROL_PLANE.auth.authenticate(api_key)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get('/', response_class=HTMLResponse)
def landing() -> str:
    return render_landing_page()


@app.get('/login', response_class=HTMLResponse)
def login() -> str:
    return render_login_page()


@app.get('/signup', response_class=HTMLResponse)
def signup() -> str:
    return render_signup_page()


@app.get('/app', response_class=HTMLResponse)
def app_shell() -> str:
    return render_app_page()


@app.get('/ui', response_class=HTMLResponse)
def ui() -> str:
    return render_app_page()


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok', service=SETTINGS.app_name)


@app.get('/v1/models', response_model=dict[str, list[ModelInfo]])
def list_models() -> dict[str, list[ModelInfo]]:
    _ = load_litellm_config()
    models = [ModelInfo(id=model_name) for model_name in list_model_names()]
    return {'data': models}


@app.get('/v1/me', response_model=AccountResponse)
def current_account(user=Depends(get_current_user)) -> AccountResponse:
    return AccountResponse(
        id=user.id,
        plan=user.plan,
        credits_cents=user.credits_cents,
        rate_limit_per_minute=user.rate_limit_per_minute,
        email=user.email,
        active=user.active,
    )


@app.get('/v1/usage/recent', response_model=UsageResponse)
def recent_usage(
    user=Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=50),
) -> UsageResponse:
    records = CONTROL_PLANE.usage.recent_for_user(user.id, limit=limit)
    items = [
        UsageItemResponse(
            model=record.model,
            tokens_in=record.tokens_in,
            tokens_out=record.tokens_out,
            cost_cents=record.cost_cents,
            created_at=record.created_at.astimezone(timezone.utc).isoformat(),
        )
        for record in records
    ]
    total_cost_cents = sum(record.cost_cents for record in records)
    total_tokens = sum(record.tokens_in + record.tokens_out for record in records)
    return UsageResponse(data=items, total_cost_cents=total_cost_cents, total_tokens=total_tokens)


@app.post('/v1/chat/completions')
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: str = Depends(require_api_key),
) -> dict[str, object]:
    try:
        user = CONTROL_PLANE.auth.authenticate(api_key)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if user.credits_cents <= 0:
        raise HTTPException(status_code=402, detail='Insufficient credits')

    decision = CONTROL_PLANE.rate_limiter.check(user.id, user.rate_limit_per_minute)
    if not decision.allowed:
        headers = {'Retry-After': str(decision.retry_after_seconds or 60)}
        raise HTTPException(status_code=429, detail='Rate limit exceeded', headers=headers)

    payload = request.model_dump(exclude_none=True)

    try:
        response = await proxy_chat_completion(payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    usage_record, estimate = CONTROL_PLANE.billing.to_usage_record(user.id, request.model, response)
    CONTROL_PLANE.usage.create(usage_record)
    CONTROL_PLANE.users.adjust_credits(user.id, -estimate.cost_cents)

    return response
