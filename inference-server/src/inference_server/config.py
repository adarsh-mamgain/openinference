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

    # Chat model (run via llama-cpp-python). "local" loads a GGUF instruct
    # model; the server has no mock/echo fallback.
    model_backend: str = "local"
    model_path: str = "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    model_identifier: str = "qwen2.5-0.5b-instruct"  # id reported by /v1/models
    model_ctx: int = 512  # context window in tokens
    model_threads: int = 2  # CPU threads for inference

    # Embedding model (dedicated GGUF that supports embedding=True).
    embedding_model_path: str = "models/nomic-embed-text-v1.5.Q8_0.gguf"
    embedding_model_identifier: str = "nomic-embed-text-v1.5"
    embedding_model_ctx: int = 512


settings = Settings()
