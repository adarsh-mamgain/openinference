from __future__ import annotations

import json
from datetime import timezone
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.control_plane import CONTROL_PLANE
from app.litellm_proxy import list_model_names, load_litellm_config, proxy_chat_completion
from app.middleware.auth import get_bearer_or_api_key, get_session_cookie
from app.models import (
    AccountResponse,
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    AuthResponse,
    CheckoutRequest,
    CheckoutResponse,
    HealthResponse,
    LoginRequest,
    MessageResponse,
    ModelInfo,
    RegisterRequest,
    UsageItemResponse,
    UsageResponse,
)
from app.services.auth import AuthenticationError, RegistrationError
from app.settings import SETTINGS
from app.ui import render_app_page, render_landing_page, render_login_page, render_signup_page


app = FastAPI(title=SETTINGS.app_name)


def _cookie_options() -> dict[str, Any]:
    return {
        'httponly': True,
        'samesite': 'lax',
        'secure': SETTINGS.app_env != 'development',
        'path': '/',
    }


def _set_session_cookie(response, token: str) -> None:
    response.set_cookie(SETTINGS.session_cookie_name, token, **_cookie_options())


def _clear_session_cookie(response) -> None:
    response.delete_cookie(SETTINGS.session_cookie_name, path='/')


def _user_to_account(user) -> AccountResponse:
    return AccountResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        plan=user.plan,
        credits_cents=user.credits_cents,
        rate_limit_per_minute=user.rate_limit_per_minute,
        active=user.active,
    )


def _api_key_to_response(api_key) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        active=api_key.active,
        created_at=api_key.created_at.astimezone(timezone.utc).isoformat(),
        last_used_at=api_key.last_used_at.astimezone(timezone.utc).isoformat() if api_key.last_used_at else None,
        revoked_at=api_key.revoked_at.astimezone(timezone.utc).isoformat() if api_key.revoked_at else None,
    )


def _require_session_user(request: Request):
    session_token = get_session_cookie(request, SETTINGS.session_cookie_name)
    try:
        return CONTROL_PLANE.auth.authenticate_session(session_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _require_customer_user(request: Request):
    auth_header = request.headers.get('authorization', '')
    x_api_key = request.headers.get('x-api-key')
    if auth_header.lower().startswith('bearer ') or x_api_key:
        api_key = get_bearer_or_api_key(request)
        try:
            return CONTROL_PLANE.auth.authenticate_api_key(api_key).user
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    if SETTINGS.session_cookie_name in request.cookies:
        return _require_session_user(request)

    raise HTTPException(status_code=401, detail='Missing API key or session')


@app.get('/', response_class=HTMLResponse)
def landing() -> str:
    return render_landing_page()


@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    if SETTINGS.session_cookie_name in request.cookies:
        try:
            _require_session_user(request)
            return RedirectResponse(url='/app', status_code=302)
        except HTTPException:
            pass
    return HTMLResponse(render_login_page())


@app.get('/signup', response_class=HTMLResponse)
def signup_page(request: Request):
    if SETTINGS.session_cookie_name in request.cookies:
        try:
            _require_session_user(request)
            return RedirectResponse(url='/app', status_code=302)
        except HTTPException:
            pass
    return HTMLResponse(render_signup_page())


@app.get('/app', response_class=HTMLResponse)
def app_page(request: Request):
    try:
        _require_session_user(request)
    except HTTPException:
        return RedirectResponse(url='/login', status_code=302)
    return HTMLResponse(render_app_page())


@app.get('/ui', response_class=HTMLResponse)
def ui(request: Request):
    return app_page(request)


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok', service=SETTINGS.app_name)


@app.post('/auth/register', response_model=AuthResponse)
def register(payload: RegisterRequest) -> JSONResponse:
    try:
        user, session_token = CONTROL_PLANE.auth.register(
            email=payload.email,
            password=payload.password,
            name=payload.name,
        )
    except RegistrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = JSONResponse({'user': _user_to_account(user).model_dump()})
    _set_session_cookie(response, session_token)
    return response


@app.post('/auth/login', response_model=AuthResponse)
def login(payload: LoginRequest) -> JSONResponse:
    try:
        user, session_token = CONTROL_PLANE.auth.login(email=payload.email, password=payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    response = JSONResponse({'user': _user_to_account(user).model_dump()})
    _set_session_cookie(response, session_token)
    return response


@app.post('/auth/logout', response_model=MessageResponse)
def logout(request: Request) -> JSONResponse:
    session_token = request.cookies.get(SETTINGS.session_cookie_name)
    if session_token:
        CONTROL_PLANE.auth.logout(session_token)
    response = JSONResponse({'message': 'Logged out'})
    _clear_session_cookie(response)
    return response


@app.get('/auth/me', response_model=AccountResponse)
def auth_me(request: Request) -> AccountResponse:
    user = _require_session_user(request)
    return _user_to_account(user)


@app.get('/v1/me', response_model=AccountResponse)
def current_account(request: Request) -> AccountResponse:
    user = _require_session_user(request)
    return _user_to_account(user)


@app.get('/v1/models', response_model=dict[str, list[ModelInfo]])
def list_models(request: Request) -> dict[str, list[ModelInfo]]:
    _ = request
    _ = load_litellm_config()
    models = [ModelInfo(id=model_name) for model_name in list_model_names()]
    return {'data': models}


@app.get('/v1/api-keys', response_model=dict[str, list[ApiKeyResponse]])
def list_api_keys(request: Request) -> dict[str, list[ApiKeyResponse]]:
    user = _require_session_user(request)
    keys = [_api_key_to_response(key) for key in CONTROL_PLANE.auth.list_api_keys(user.id)]
    return {'data': keys}


@app.post('/v1/api-keys', response_model=ApiKeyCreatedResponse)
def create_api_key(request: Request, payload: ApiKeyCreateRequest) -> ApiKeyCreatedResponse:
    user = _require_session_user(request)
    api_key, secret = CONTROL_PLANE.auth.create_api_key(user_id=user.id, name=payload.name)
    return ApiKeyCreatedResponse(key=_api_key_to_response(api_key), secret=secret)


@app.delete('/v1/api-keys/{key_id}', response_model=ApiKeyResponse)
def revoke_api_key(request: Request, key_id: str) -> ApiKeyResponse:
    user = _require_session_user(request)
    revoked = CONTROL_PLANE.auth.revoke_api_key(user.id, key_id)
    return _api_key_to_response(revoked)


@app.get('/v1/usage/recent', response_model=UsageResponse)
def recent_usage(request: Request, limit: int = Query(default=10, ge=1, le=50)) -> UsageResponse:
    user = _require_session_user(request)
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


@app.post('/v1/billing/checkout', response_model=CheckoutResponse)
def create_checkout(request: Request, payload: CheckoutRequest) -> CheckoutResponse:
    user = _require_session_user(request)
    checkout = CONTROL_PLANE.payments.create_credit_checkout(
        user_email=user.email,
        user_name=user.name,
        amount_cents=payload.amount_cents,
        return_url=f'{SETTINGS.base_url}/app?checkout=success',
        cancel_url=f'{SETTINGS.base_url}/app?checkout=cancelled',
    )
    return CheckoutResponse(session_id=checkout['session_id'], checkout_url=checkout['checkout_url'])


@app.post('/webhooks/dodo', response_model=MessageResponse)
def dodo_webhook(payload: dict = Body(...)) -> MessageResponse:
    event_type = payload.get('event_type') or payload.get('type') or ''
    data = payload.get('data') or payload.get('payload') or payload
    if 'succeeded' not in event_type and data.get('payment_status') != 'succeeded':
        return MessageResponse(message='ignored')

    metadata = data.get('metadata') or payload.get('metadata') or {}
    user_id = metadata.get('user_id')
    credits_cents = int(metadata.get('credits_cents') or metadata.get('credit_amount_cents') or 0)
    if user_id and credits_cents > 0:
        CONTROL_PLANE.auth.top_up_credits(user_id, credits_cents)
    return MessageResponse(message='ok')


@app.post('/v1/chat/completions')
async def chat_completions(request: Request, payload: ChatCompletionRequest = Body(...)) -> dict[str, object]:
    user = _require_customer_user(request)

    if user.credits_cents <= 0:
        raise HTTPException(status_code=402, detail='Insufficient credits')

    decision = CONTROL_PLANE.rate_limiter.check(user.id, user.rate_limit_per_minute)
    if not decision.allowed:
        headers = {'Retry-After': str(decision.retry_after_seconds or 60)}
        raise HTTPException(status_code=429, detail='Rate limit exceeded', headers=headers)

    body = payload.model_dump(exclude_none=True)

    try:
        response = await proxy_chat_completion(body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    usage_record, estimate = CONTROL_PLANE.billing.to_usage_record(user.id, payload.model, response)
    CONTROL_PLANE.usage.create(usage_record)
    CONTROL_PLANE.auth.debit_credits(user.id, estimate.cost_cents)

    return response
