"""Application settings loaded from environment variables.

Pydantic-settings reads from a `.env` file and/or the process environment.
This keeps secrets (like API keys) out of the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "inference-server"
    api_key: str = "dev-key"  # any key is accepted when this is unset

    rate_limit_max_requests: int = 100  # per key, per window
    rate_limit_window_seconds: int = 60

    # Model backend. "local" loads a GGUF model via llama-cpp-python;
    # "mock" falls back to the deterministic echo model.
    model_backend: str = "local"
    model_path: str = "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    model_ctx: int = 512  # context window in tokens
    model_threads: int = 2  # CPU threads for inference


settings = Settings()
