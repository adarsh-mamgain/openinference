from dataclasses import dataclass
import os
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
    redis_host: str = os.getenv('REDIS_HOST', 'localhost')
    redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
    database_url: str = os.getenv(
        'DATABASE_URL',
        'postgresql://user:pass@localhost:5432/oss_router',
    )
    dev_api_key: str = os.getenv('OPENROUTER_DEV_API_KEY', '')
    default_rate_limit_per_minute: int = int(os.getenv('DEFAULT_RATE_LIMIT_PER_MINUTE', '60'))
    default_credits_cents: int = int(os.getenv('DEFAULT_CREDITS_CENTS', '1000'))
    app_root: Path = ROOT
    litellm_config_path: Path = PATHS.litellm_config
    providers_path: Path = PATHS.providers


SETTINGS = AppSettings()
