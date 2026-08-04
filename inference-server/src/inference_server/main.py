"""FastAPI application entrypoint for the inference server."""

from fastapi import FastAPI

from inference_server.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health check for probes and uptime monitors."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    """Human-friendly landing response."""
    return {"service": settings.app_name, "docs": "/docs"}
