"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "scheduler"

    # Worker pool
    num_workers: int = 2  # how many jobs process concurrently
    max_queue_size: int = 1000  # backpressure limit; submit returns 429 when full
    worker_poll_seconds: float = 0.05

    # Backend
    # "simulated" processes jobs with an artificial delay so the scheduling
    # machinery can be exercised without a real model loaded.
    backend: str = "simulated"

    # Simulated backend timing (seconds per job by default)
    simulated_default_seconds: float = 1.0


settings = Settings()
