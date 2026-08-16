"""Scheduler settings loaded from environment variables.

This is a library used inside the inference-server; only the worker pool
settings live here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    num_workers: int = 2  # how many jobs generate concurrently
    max_queue_size: int = 1000  # backpressure limit; submit blocks when full
    max_in_flight: int = 4  # admission control: reject submits beyond this
                            # (queued + running) so the box never drowns


settings = Settings()
