from __future__ import annotations

import json
from datetime import timezone
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from app.control_plane import CONTROL_PLANE
from app.litellm_proxy import list_model_names, load_litellm_config, proxy_chat_completion, proxy_chat_completion_stream
from app.middleware.auth import get_bearer_or_api_key, get_session_cookie
from app.models import (
    AccountResponse,
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    AuthResponse,
    ChatCompletionRequest,
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
from app.services.auth import AuthenticationError, InsufficientCreditsError, RegistrationError
from app.settings import SETTINGS
from app.ui import render_app_page, render_landing_page, render_login_page, render_signup_page


app = FastAPI(title=SETTINGS.app_name)


# ── Cookie helpers ─────────────────────────────────────────────────────────

def _cookie_options() -> dict[str, Any]:
    return {
        'httponly': True,
        'samesite': 'lax',
        'secure': SETTINGS.app_env != 'development',
        'path': '/',
    }


def _set_session_cookie(response: JSONResponse, token: str) -> None:
    response.set_cookie(SETTINGS.session_cookie_name, token, **_cookie_options())


def _clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(SETTINGS.session_cookie_name, path='/')


# ── Serialisation helpers ──────────────────────────────────────────────────

def _user_to_account(user: Any) -> AccountResponse:
    return AccountResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        plan=user.plan,
        credits_cents=user.credits_cents,
        rate_limit_per_minute=user.rate_limit_per_minute,
        active=user.active,
    )


def _api_key_to_response(api_key: Any) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        active=api_key.active,
        created_at=api_key.created_at.astimezone(timezone.utc).isoformat(),
        last_used_at=(
            api_key.last_used_at.astimezone(timezone.utc).isoformat()
            if api_key.last_used_at
            else None
        ),
        revoked_at=(
            api_key.revoked_at.astimezone(timezone.utc).isoformat()
            if api_key.revoked_at
            else None
        ),
    )


# ── Auth guards ────────────────────────────────────────────────────────────

def _require_session_user(request: Request) -> Any:
    session_token = get_session_cookie(request, SETTINGS.session_cookie_name)
    try:
        return CONTROL_PLANE.auth.authenticate_session(session_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _require_customer_user(request: Request) -> Any:
    """Accept either a Bearer/X-API-Key token or a session cookie."""
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


# ── UI routes ──────────────────────────────────────────────────────────────

@app.get('/', response_class=HTMLResponse)
def landing() -> str:
    return render_landing_page()


@app.get('/login', response_class=HTMLResponse, response_model=None)
def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    if SETTINGS.session_cookie_name in request.cookies:
        try:
            _require_session_user(request)
            return RedirectResponse(url='/app', status_code=302)
        except HTTPException:
            pass
    return HTMLResponse(render_login_page())


@app.get('/signup', response_class=HTMLResponse, response_model=None)
def signup_page(request: Request) -> HTMLResponse | RedirectResponse:
    if SETTINGS.session_cookie_name in request.cookies:
        try:
            _require_session_user(request)
            return RedirectResponse(url='/app', status_code=302)
        except HTTPException:
            pass
    return HTMLResponse(render_signup_page())


@app.get('/app', response_class=HTMLResponse, response_model=None)
def app_page(request: Request) -> HTMLResponse | RedirectResponse:
    try:
        _require_session_user(request)
    except HTTPException:
        return RedirectResponse(url='/login', status_code=302)
    return HTMLResponse(render_app_page())


@app.get('/ui', response_class=HTMLResponse, response_model=None)
def ui(request: Request) -> HTMLResponse | RedirectResponse:
    return app_page(request)


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok', service=SETTINGS.app_name)


# ── Auth endpoints ─────────────────────────────────────────────────────────

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
    return _user_to_account(_require_session_user(request))


# ── v1 API ─────────────────────────────────────────────────────────────────

@app.get('/v1/me', response_model=AccountResponse)
def current_account(request: Request) -> AccountResponse:
    return _user_to_account(_require_session_user(request))


@app.get('/v1/models')
def list_models() -> dict[str, list[ModelInfo]]:
    load_litellm_config()  # validates config is readable
    return {'data': [ModelInfo(id=name) for name in list_model_names()]}


@app.get('/v1/api-keys', response_model=dict[str, list[ApiKeyResponse]])
def list_api_keys(request: Request) -> dict[str, list[ApiKeyResponse]]:
    user = _require_session_user(request)
    return {'data': [_api_key_to_response(k) for k in CONTROL_PLANE.auth.list_api_keys(user.id)]}


@app.post('/v1/api-keys', response_model=ApiKeyCreatedResponse)
def create_api_key(request: Request, payload: ApiKeyCreateRequest) -> ApiKeyCreatedResponse:
    user = _require_session_user(request)
    api_key, secret = CONTROL_PLANE.auth.create_api_key(user_id=user.id, name=payload.name)
    return ApiKeyCreatedResponse(key=_api_key_to_response(api_key), secret=secret)


@app.delete('/v1/api-keys/{key_id}', response_model=ApiKeyResponse)
def revoke_api_key(request: Request, key_id: str) -> ApiKeyResponse:
    user = _require_session_user(request)
    return _api_key_to_response(CONTROL_PLANE.auth.revoke_api_key(user.id, key_id))


@app.get('/v1/usage/recent', response_model=UsageResponse)
def recent_usage(
    request: Request, limit: int = Query(default=10, ge=1, le=50)
) -> UsageResponse:
    user = _require_session_user(request)
    records = CONTROL_PLANE.usage.recent_for_user(user.id, limit=limit)
    items = [
        UsageItemResponse(
            model=r.model,
            tokens_in=r.tokens_in,
            tokens_out=r.tokens_out,
            cost_cents=r.cost_cents,
            created_at=r.created_at.astimezone(timezone.utc).isoformat(),
        )
        for r in records
    ]
    return UsageResponse(
        data=items,
        total_cost_cents=sum(r.cost_cents for r in records),
        total_tokens=sum(r.tokens_in + r.tokens_out for r in records),
    )


@app.post('/v1/billing/checkout', response_model=CheckoutResponse)
def create_checkout(request: Request, payload: CheckoutRequest) -> CheckoutResponse:
    user = _require_session_user(request)
    checkout = CONTROL_PLANE.payments.create_credit_checkout(
        user_email=user.email,
        user_name=user.name,
        amount_cents=payload.amount_cents,
        return_url=f'{SETTINGS.base_url}/app?checkout=success',
        cancel_url=f'{SETTINGS.base_url}/app?checkout=cancelled',
        user_id=user.id,
    )
    return CheckoutResponse(
        session_id=checkout['session_id'],
        checkout_url=checkout['checkout_url'],
    )


# ── Chat completions ───────────────────────────────────────────────────────

@app.post('/v1/chat/completions')
async def chat_completions(
    request: Request,
    payload: ChatCompletionRequest = Body(...),
) -> Any:
    user = _require_customer_user(request)

    # Gate on credits BEFORE hitting the provider
    if user.credits_cents <= 0:
        raise HTTPException(status_code=402, detail='Insufficient credits. Top up at /app.')

    decision = CONTROL_PLANE.rate_limiter.check(user.id, user.rate_limit_per_minute)
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail='Rate limit exceeded',
            headers={'Retry-After': str(decision.retry_after_seconds or 60)},
        )

    body = payload.model_dump(exclude_none=True)
    wants_stream = body.get('stream', False)

    if wants_stream:
        # Streaming path — billing happens after the stream ends
        # (cost is logged by the generator; we can't debit mid-stream)
        async def _stream_and_bill() -> Any:
            async for chunk in proxy_chat_completion_stream(body):
                yield chunk
            # Post-stream: bill a flat estimate based on model + rough token count
            # Full token accounting requires parsing every chunk — overkill for MVP.
            # Use a conservative estimate of 500 tokens for streaming calls.
            estimate_tokens = 500
            estimate = CONTROL_PLANE.billing.estimate_usage(
                model=payload.model, tokens_in=estimate_tokens, tokens_out=estimate_tokens
            )
            try:
                CONTROL_PLANE.auth.debit_credits(user.id, estimate.cost_cents)
            except InsufficientCreditsError:
                pass  # Already served — just don't go further negative

        return StreamingResponse(
            _stream_and_bill(),
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            },
        )

    # Non-streaming path
    try:
        response = await proxy_chat_completion(body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    usage_record, estimate = CONTROL_PLANE.billing.to_usage_record(user.id, payload.model, response)
    CONTROL_PLANE.usage.create(usage_record)

    try:
        CONTROL_PLANE.auth.debit_credits(user.id, estimate.cost_cents)
    except InsufficientCreditsError:
        # Edge case: user had exactly enough to pass the gate but the actual cost
        # was higher. Serve the response — the atomic debit will floor at 0.
        pass

    return response


# ── Webhooks ───────────────────────────────────────────────────────────────

@app.post('/webhooks/dodo', response_model=MessageResponse)
async def dodo_webhook(request: Request) -> MessageResponse:
    """Verify Dodo Payments webhook signature via Standard Webhooks spec.

    Dodo sends ``webhook-id``, ``webhook-signature``, and
    ``webhook-timestamp`` headers with an HMAC-SHA256 of
    ``{id}.{timestamp}.{body}``, keyed with ``DODO_WEBHOOK_SECRET``.

    Falls back to skipping verification if the secret is not configured
    (unsafe — warn and allow, but not for production).
    """
    from standardwebhooks import Webhook, WebhookVerificationError

    raw_body = await request.body()

    webhook_secret = getattr(SETTINGS, 'dodo_webhook_secret', '') or ''
    if webhook_secret:
        wh = Webhook(webhook_secret)
        try:
            wh.verify(
                raw_body,
                {
                    'webhook-id': request.headers.get('webhook-id', ''),
                    'webhook-signature': request.headers.get('webhook-signature', ''),
                    'webhook-timestamp': request.headers.get('webhook-timestamp', ''),
                },
            )
        except WebhookVerificationError:
            raise HTTPException(status_code=400, detail='Invalid webhook signature')
    else:
        import logging
        logging.getLogger(__name__).warning(
            'DODO_WEBHOOK_SECRET not set — skipping signature verification. '
            'This is unsafe in production.'
        )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail='Invalid JSON') from exc

    event_type = payload.get('type', '')
    data = payload.get('data', payload)

    if 'succeeded' not in event_type:
        return MessageResponse(message='ignored')

    metadata = data.get('metadata') or {}
    user_id = metadata.get('user_id')
    credits_cents = int(metadata.get('credits_cents', 0))

    if user_id and credits_cents > 0:
        CONTROL_PLANE.auth.top_up_credits(user_id, credits_cents)

    return MessageResponse(message='ok')
