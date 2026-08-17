"""The routing engine.

``Router`` holds the set of registered :class:`Route`\\ s and picks one per
request. Selection is scored across three axes — quality, cost, latency — using
client hints when present, then adjusted by each route's recent health.

The decision is explainable: every choice carries a ``reason`` string and the
ordered fallback list, so you (and an interviewer) can see *why* a route won.
"""

import logging

from inference_server.router.health import RouteHealth
from inference_server.router.models import (
    Route,
    RouteBackend,
    RouteHints,
    RoutingDecision,
)

logger = logging.getLogger(__name__)


def _score(route: Route, hints: RouteHints) -> tuple[float, list[str]]:
    """Return (score, list of reason fragments) for a route against hints.

    Each axis contributes ``weight * value``; the weights react to client
    hints so a quality-seeking client weighs quality more, a cost-conscious one
    weighs cost more, etc. All values are 0-1 with 1 = best.
    """
    notes: list[str] = []

    quality_weight = 0.5 + 0.5 * (hints.quality if hints.quality is not None else 0.0)
    latency_weight = 0.5 + 0.5 * (hints.latency_budget_ms is not None)
    cost_weight = 0.5 + 2.0 * (hints.cost_sensitivity if hints.cost_sensitivity is not None else 0.0)

    # Latency value: how close the route is to the requested budget (or fast).
    if hints.latency_budget_ms is not None:
        budget = hints.latency_budget_ms
        latency_value = 1.0 if route.latency_ms <= budget else max(
            0.0, 1.0 - (route.latency_ms / budget - 1.0)
        )
        notes.append(f"latency {route.latency_ms:.0f}ms budget {budget:.0f}ms")
    else:
        latency_value = max(0.0, 1.0 - (route.latency_ms / 1000.0))
        notes.append(f"est {route.latency_ms:.0f}ms")

    cost_value = max(0.0, 1.0 - (route.cost_per_1k_tokens / 5.0))
    if route.cost_per_1k_tokens:
        notes.append(f"cost ${route.cost_per_1k_tokens:.4f}/1k")

    total = quality_weight + latency_weight + cost_weight
    score = (
        quality_weight * route.quality
        + latency_weight * latency_value
        + cost_weight * cost_value
    ) / total
    notes.append(f"q{route.quality:.2f}")

    return (score, notes)


class Router:
    def __init__(
        self,
        routes: list[Route] | None = None,
        health: RouteHealth | None = None,
    ) -> None:
        self._routes: dict[str, Route] = {r.id: r for r in (routes or [])}
        self.health = health or RouteHealth()

    def register(self, route: Route) -> None:
        self._routes[route.id] = route

    def routes(self) -> list[Route]:
        return list(self._routes.values())

    def get(self, route_id: str) -> Route | None:
        return self._routes.get(route_id)

    # -- selection ---------------------------------------------------------

    def _eligible(self) -> list[Route]:
        return [
            r
            for r in self._routes.values()
            if r.enabled
            and r.available()
            and self.health.healthy(r.id)
        ]

    def route(self, requested: str | None = None, hints: RouteHints | None = None) -> RoutingDecision:
        """Pick the best route for a request.

        ``requested`` is an explicit model id from the client (e.g. the ``model``
        field in a chat request). If it matches a registered route and that route
        is healthy, it wins immediately. Otherwise we score all eligible routes.
        """
        hints = hints or RouteHints()

        if requested:
            exact = self._routes.get(requested)
            if exact is not None and exact.enabled and exact.available():
                if self.health.healthy(exact.id):
                    return RoutingDecision(
                        route=exact,
                        reason=f"explicit request for '{requested}' and route is healthy",
                        considered=[requested],
                        fallback_order=self._fallback_order(exact.id),
                    )
                # Explicitly requested but unhealthy: fall through to scoring,
                # noting the preferred route is on cooldown.
                return self._scored_decision(hints, preferred=requested)

        return self._scored_decision(hints)

    def _scored_decision(self, hints: RouteHints, preferred: str | None = None) -> RoutingDecision:
        eligible = self._eligible()
        if not eligible:
            # Even an unhealthy/explicit route is better than nothing: surface
            # it so the caller can emit a clear "model unavailable" response.
            raise ValueError("no eligible route")

        scored = [(r, *_score(r, hints)) for r in eligible]
        scored.sort(key=lambda s: s[1], reverse=True)
        best, best_score, best_notes = scored[0]

        reasons = []
        if preferred:
            reasons.append(f"preferred '{preferred}' is unhealthy/on cooldown")
        reasons.append(f"scored best at {best_score:.3f} ({', '.join(best_notes)})")

        return RoutingDecision(
            route=best,
            reason="; ".join(reasons),
            considered=[r.id for r, *_ in scored],
            fallback_order=self._fallback_order(best.id),
        )

    def _fallback_order(self, route_id: str) -> list[str]:
        """Order the remaining routes as fallbacks (best first)."""
        rest = sorted(
            self._routes.values(),
            key=lambda r: (0 if r.id == route_id else 1, r.quality),
            reverse=True,
        )
        return [r.id for r in rest if r.id != route_id]

    def next_fallback(self, decision: RoutingDecision) -> Route | None:
        """Return the next untried healthy fallback for a failed decision.

        Returns ``None`` when there are no more fallbacks left.
        """
        for rid in decision.fallback_order:
            route = self._routes.get(rid)
            if (
                route is not None
                and route.enabled
                and route.available()
                and self.health.healthy(rid)
            ):
                return route
        return None

    # -- feedback ----------------------------------------------------------

    def report_outcome(self, route_id: str, ok: bool) -> None:
        self.health.record(route_id, ok)

    def health_snapshot(self) -> dict:
        return self.health.snapshot()

    def status(self) -> dict:
        return {
            "routes": [
                {
                    "id": r.id,
                    "backend": r.backend.value,
                    "quality": r.quality,
                    "cost_per_1k_tokens": r.cost_per_1k_tokens,
                    "latency_ms": r.latency_ms,
                    "available": r.available(),
                    "enabled": r.enabled,
                }
                for r in self._routes.values()
            ],
            "health": self.health_snapshot(),
        }
