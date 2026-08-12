"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "scheduler"

    # Worker pool
    num_workers: int = 2  # how many jobs generate concurrently
    max_queue_size: int = 1000  # backpressure limit; submit blocks when full


settings = Settings()
