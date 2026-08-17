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
    job_timeout_seconds: float = 120.0  # per-job ceiling; a hung generation
                                        # fails instead of wedging a worker
    shutdown_grace_seconds: float = 10.0  # how long stop() waits for in-flight
                                          # jobs before cancelling them


settings = Settings()
