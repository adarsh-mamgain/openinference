from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from config.settings import PATHS, ROOT

load_dotenv()


@dataclass(frozen=True)
class AppSettings:
    app_name: str = os.getenv('APP_NAME', 'OpenRouter OSS')
    app_env: str = os.getenv('APP_ENV', 'development')
    host: str = os.getenv('APP_HOST', '0.0.0.0')
    port: int = int(os.getenv('APP_PORT', '8000'))
    base_url: str = os.getenv('APP_BASE_URL', 'http://localhost:8000')
    redis_host: str = os.getenv('REDIS_HOST', 'localhost')
    redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
    database_url: str = os.getenv(
        'DATABASE_URL',
        'postgresql://user:pass@localhost:5432/oss_router',
    )
    session_cookie_name: str = os.getenv('SESSION_COOKIE_NAME', 'openrouter_session')
    dev_email: str = os.getenv('OPENROUTER_DEV_EMAIL', '')
    dev_password: str = os.getenv('OPENROUTER_DEV_PASSWORD', '')
    default_rate_limit_per_minute: int = int(os.getenv('DEFAULT_RATE_LIMIT_PER_MINUTE', '60'))
    default_credits_cents: int = int(os.getenv('DEFAULT_CREDITS_CENTS', '0'))
    dodo_api_key: str = os.getenv('DODO_PAYMENTS_API_KEY', '')
    dodo_environment: str = os.getenv('DODO_PAYMENTS_ENVIRONMENT', 'test_mode')
    dodo_product_id: str = os.getenv('DODO_PRODUCT_ID', '')
    dodo_webhook_secret: str = os.getenv('DODO_WEBHOOK_SECRET', '')
    app_root: Path = ROOT
    litellm_config_path: Path = PATHS.litellm_config
    providers_path: Path = PATHS.providers


SETTINGS = AppSettings()
