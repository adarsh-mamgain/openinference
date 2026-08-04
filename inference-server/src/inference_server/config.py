"""Application settings loaded from environment variables.

Pydantic-settings reads from a `.env` file and/or the process environment.
This keeps secrets (like API keys) out of the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "inference-server"
    api_key: str = "dev-key"  # any key is accepted when this is unset


settings = Settings()
