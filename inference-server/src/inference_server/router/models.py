"""Data models for the routing engine.

A *route* describes one concrete way to serve a chat completion: a local GGUF
through llama.cpp, or (in future) a remote provider endpoint. The router
chooses among routes for each request based on quality/latency/cost preferences
and per-route health.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class RouteBackend(str, Enum):
    LOCAL = "local"          # a GGUF served via llama.cpp
    PROVIDER = "provider"    # an OpenAI-compatible HTTP endpoint


@dataclass
class Route:
    """A single candidate for serving a chat completion."""

    id: str
    backend: RouteBackend = RouteBackend.LOCAL
    # local backend
    model_path: str | None = None
    model_identifier: str | None = None
    n_ctx: int = 512
    # provider backend
    provider_url: str | None = None
    provider_api_key: str | None = None
    # scoring attributes (0-1, higher = better)
    quality: float = 0.5
    cost_per_1k_tokens: float = 0.0  # USD
    latency_ms: float = 100.0        # estimated p50 per request
    max_context: int = 4096
    enabled: bool = True
    # dynamic availability probe; defaults to the static file/url check.
    available_check: Callable[[], bool] | None = None

    def available(self) -> bool:
        if self.available_check is not None:
            return self.available_check()
        if self.backend == RouteBackend.LOCAL:
            if self.model_path is None:
                return False
            from pathlib import Path

            return Path(self.model_path).is_file()
        return bool(self.provider_url)


@dataclass
class RouteHints:
    """Client-supplied preferences steering route selection.

    All fields optional: absent fields mean "don't care" and the route is
    scored on the rest.
    """

    quality: float | None = None        # 0-1, 1 = demand best quality
    latency_budget_ms: float | None = None  # reject slower than this
    cost_sensitivity: float | None = None   # 0 = cost-agnostic, 1 = cheapest


@dataclass
class RoutingDecision:
    """The outcome of routing a request, with the reasoning attached."""

    route: Route
    reason: str
    considered: list[str] = field(default_factory=list)
    fallback_order: list[str] = field(default_factory=list)
