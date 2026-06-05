from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import yaml

try:
    import litellm
except Exception:  # pragma: no cover - optional runtime dependency
    litellm = None

from app.settings import SETTINGS


def load_litellm_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or SETTINGS.litellm_config_path
    with config_path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle) or {}


def list_model_names() -> list[str]:
    config = load_litellm_config()
    return [model['model_name'] for model in config.get('model_list', [])]


def resolve_model(model_name: str) -> dict[str, Any]:
    config = load_litellm_config()
    for model in config.get('model_list', []):
        if model.get('model_name') == model_name:
            return model
    raise KeyError(f'Unknown model: {model_name}')


def build_completion_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    model_entry = resolve_model(payload['model'])
    litellm_params = model_entry.get('litellm_params', {})
    api_key_ref = str(litellm_params.get('api_key', '')).replace('os.environ/', '')
    api_key = os.getenv(api_key_ref) if api_key_ref else None

    completion_kwargs = {key: value for key, value in payload.items() if key != 'api_key'}
    completion_kwargs['model'] = litellm_params.get('model', payload['model'])
    if api_key:
        completion_kwargs['api_key'] = api_key

    return completion_kwargs


async def proxy_chat_completion(payload: dict[str, Any]) -> Any:
    if litellm is None:
        raise RuntimeError('litellm is not installed')

    completion_kwargs = build_completion_kwargs(payload)
    return await asyncio.to_thread(litellm.completion, **completion_kwargs)
