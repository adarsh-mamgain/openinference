from __future__ import annotations

import os
from pathlib import Path
from typing import Any, AsyncIterator

import yaml

try:
    import litellm
    from litellm import Router
except Exception:  # pragma: no cover
    litellm = None  # type: ignore[assignment]
    Router = None  # type: ignore[assignment, misc]

from app.settings import SETTINGS

# ── Silence litellm's verbose success logs ─────────────────────────────────
if litellm is not None:
    litellm.success_callback = []
    litellm.failure_callback = []


# ── Config loading ─────────────────────────────────────────────────────────

def load_litellm_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or SETTINGS.litellm_config_path
    with config_path.open('r', encoding='utf-8') as fh:
        return yaml.safe_load(fh) or {}


def list_model_names() -> list[str]:
    config = load_litellm_config()
    return [m['model_name'] for m in config.get('model_list', [])]


# ── Router singleton ───────────────────────────────────────────────────────
# Built once at import time. If the YAML changes at runtime, call
# rebuild_router() explicitly (useful in tests).

_router: Router | None = None


def _build_router() -> Router:
    """Construct a LiteLLM Router from litellm_config.yaml.

    Each model entry's litellm_params.api_key may be written as
    ``os.environ/VAR_NAME``.  LiteLLM Router resolves these natively, so we
    do NOT need to touch them.
    """
    if Router is None:
        raise RuntimeError('litellm is not installed')

    config = load_litellm_config()
    model_list = config.get('model_list', [])
    if not model_list:
        raise RuntimeError('litellm_config.yaml has no model_list entries')

    return Router(
        model_list=model_list,
        # Retry each provider up to 2 times before giving up
        num_retries=2,
        # Timeout per individual attempt (seconds)
        timeout=int(config.get('general_settings', {}).get('request_timeout', 120)),
        # Emit nothing to stdout
        set_verbose=False,
    )


def get_router() -> Router:
    global _router
    if _router is None:
        _router = _build_router()
    return _router


def rebuild_router() -> None:
    """Force-rebuild the router (e.g. after YAML changes in tests)."""
    global _router
    _router = _build_router()


# ── Model validation ───────────────────────────────────────────────────────

def _assert_model_known(model_name: str) -> None:
    """Raise KeyError early if the requested model is not in our catalog."""
    known = set(list_model_names())
    if model_name not in known:
        raise KeyError(
            f"Unknown model '{model_name}'. Available: {sorted(known)}"
        )


# ── Non-streaming completion ───────────────────────────────────────────────

async def proxy_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    """Proxy a non-streaming chat completion through LiteLLM Router.

    Args:
        payload: The validated request body dict (model, messages, …).
                 ``stream`` must be absent or False.

    Returns:
        OpenAI-compatible response dict.

    Raises:
        KeyError: model not in catalog.
        RuntimeError: litellm not installed or provider error.
    """
    if litellm is None:
        raise RuntimeError('litellm is not installed')

    model_name = payload.get('model', '')
    _assert_model_known(model_name)

    # Strip keys that LiteLLM Router doesn't want forwarded
    kwargs: dict[str, Any] = {
        k: v for k, v in payload.items()
        if k not in ('api_key', 'stream')
    }
    kwargs['stream'] = False  # explicit — never let this leak through

    router = get_router()
    try:
        response = await router.acompletion(**kwargs)
    except Exception as exc:
        # Surface as RuntimeError so main.py can map it to 503
        raise RuntimeError(f'LiteLLM error: {exc}') from exc

    return _serialize(response)


# ── Streaming completion ───────────────────────────────────────────────────

async def proxy_chat_completion_stream(
    payload: dict[str, Any],
) -> AsyncIterator[str]:
    """Stream a chat completion as SSE chunks.

    Yields raw ``data: {...}\\n\\n`` lines suitable for a StreamingResponse.
    Finishes with ``data: [DONE]\\n\\n``.
    """
    if litellm is None:
        raise RuntimeError('litellm is not installed')

    import json

    model_name = payload.get('model', '')
    _assert_model_known(model_name)

    kwargs: dict[str, Any] = {
        k: v for k, v in payload.items()
        if k not in ('api_key',)
    }
    kwargs['stream'] = True

    router = get_router()
    try:
        response = await router.acompletion(**kwargs)
    except Exception as exc:
        raise RuntimeError(f'LiteLLM error: {exc}') from exc

    async for chunk in response:
        chunk_dict = _serialize(chunk)
        yield f'data: {json.dumps(chunk_dict)}\n\n'

    yield 'data: [DONE]\n\n'


# ── Serialisation helper ───────────────────────────────────────────────────

def _serialize(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, 'model_dump'):
        return response.model_dump()
    if hasattr(response, 'dict'):
        return response.dict()
    if hasattr(response, '__dict__'):
        return dict(response.__dict__)
    raise TypeError(f'Unsupported completion response type: {type(response)}')