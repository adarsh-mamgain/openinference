"""FastAPI application entrypoint for the inference server."""

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse

from inference_server.auth import require_api_key
from inference_server.config import settings
from inference_server.landing import landing_page
from inference_server.rate_limit import RateLimiter, make_rate_limit_dependency
from inference_server.routers import chat, embeddings, models

app = FastAPI(title=settings.app_name, version="0.1.0")

_limiter = RateLimiter(
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
_rate_limit = make_rate_limit_dependency(_limiter)

app.include_router(
    chat.router,
    prefix="/v1",
    tags=["chat"],
    dependencies=[Depends(require_api_key), Depends(_rate_limit)],
)
app.include_router(
    embeddings.router,
    prefix="/v1",
    tags=["embeddings"],
    dependencies=[Depends(require_api_key), Depends(_rate_limit)],
)
app.include_router(
    models.router,
    prefix="/v1",
    tags=["models"],
    dependencies=[Depends(require_api_key), Depends(_rate_limit)],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health check for probes and uptime monitors."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Beautiful landing page explaining the product, one CTA to /docs."""
    return landing_page()
