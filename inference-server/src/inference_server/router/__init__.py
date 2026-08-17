"""Model/backend routing for the inference server.

Given a chat request, the router picks which model or backend should serve it —
trading quality, cost, latency and per-route health, and falling back when the
primary route fails. The engine (``engine.Router``) is pure logic; the chat
router wires it into ``POST /v1/chat/completions``.
"""

from inference_server.router.engine import Router
from inference_server.router.health import RouteHealth
from inference_server.router.models import (
    Route,
    RouteBackend,
    RouteHints,
    RoutingDecision,
)
from inference_server.router.registry import build_routes, default_route

__all__ = [
    "Route",
    "RouteBackend",
    "RouteHints",
    "RouteHealth",
    "RoutingDecision",
    "Router",
    "build_routes",
    "default_route",
]
