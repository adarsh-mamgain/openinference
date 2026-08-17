"""Tests for the routing engine and its wiring into the chat endpoint.

The engine tests are pure logic (no HTTP, no scheduler). The wiring test drives
the real FastAPI app with a fake model through the scheduler, asserting that a
failed primary route is retried on a healthy fallback.
"""

import tempfile
from pathlib import Path

import httpx2
import pytest

import scheduler.scheduler as sched_module
from inference_server import main as app_module
from inference_server.router import (
    Route,
    RouteBackend,
    RouteHints,
    Router,
)
from inference_server.routers import chat as chat_module
from scheduler.scheduler import Scheduler


class _FakeModel:
    """Instant model that can be told to fail on demand."""

    def __init__(self) -> None:
        self.available = True
        self.fail_on: set[str] = set()

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def generate(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        if content in self.fail_on:
            raise RuntimeError("injected model failure")
        return f"done:{content}", None, "stop"

    def stream(self, messages, max_tokens, tools=None):
        content = messages[-1].content or ""
        if content in self.fail_on:
            return
        yield f"tok:{content}"


def _local_route(tmpdir: str, route_id: str, available: bool = True) -> Route:
    path = Path(tmpdir) / f"{route_id}.gguf"
    if available:
        path.touch()
    return Route(
        id=route_id,
        backend=RouteBackend.LOCAL,
        model_path=str(path),
        quality=0.5,
        cost_per_1k_tokens=0.0,
        latency_ms=500,
    )


# ---------------------------------------------------------------------------
# Engine unit tests
# ---------------------------------------------------------------------------


def test_route_explicit_request_wins_when_healthy(tmp_path):
    primary = _local_route(str(tmp_path), "primary")
    backup = _local_route(str(tmp_path), "backup")
    router = Router(routes=[primary, backup])

    decision = router.route(requested="primary")

    assert decision.route.id == "primary"
    assert "explicit request" in decision.reason
    assert "backup" in decision.fallback_order


def test_route_respects_quality_hint(tmp_path):
    cheap = _local_route(str(tmp_path), "cheap")
    premium = _local_route(str(tmp_path), "premium")
    premium.quality = 0.95
    cheap.quality = 0.3
    premium.cost_per_1k_tokens = 4.0
    router = Router(routes=[cheap, premium])

    quality_decision = router.route(hints=RouteHints(quality=1.0))
    cost_decision = router.route(hints=RouteHints(cost_sensitivity=1.0))

    assert quality_decision.route.id == "premium"
    assert cost_decision.route.id == "cheap"
    assert "scored best" in quality_decision.reason


def test_route_falls_back_when_primary_on_cooldown(tmp_path):
    primary = _local_route(str(tmp_path), "primary")
    backup = _local_route(str(tmp_path), "backup")
    router = Router(routes=[primary, backup])

    # Primary fails repeatedly -> goes into cooldown after the threshold.
    for _ in range(3):
        router.report_outcome("primary", ok=False)

    decision = router.route(requested="primary")

    assert router.health.healthy("primary") is False
    assert decision.route.id == "backup"
    assert "unhealthy" in decision.reason or "cooldown" in decision.reason


def test_next_fallback_returns_only_untried_and_healthy(tmp_path):
    primary = _local_route(str(tmp_path), "primary")
    backup = _local_route(str(tmp_path), "backup")
    dead = _local_route(str(tmp_path), "dead")
    router = Router(routes=[primary, backup, dead])
    for _ in range(3):
        router.report_outcome("dead", ok=False)

    decision = router.route(requested="primary")

    first = router.next_fallback(decision)
    assert first is not None and first.id != "primary"
    # The dead route must never surface as a fallback while unhealthy.
    second = router.next_fallback(
        type(decision)(route=decision.route, reason=decision.reason,
                       fallback_order=[f for f in decision.fallback_order if f != "backup"])
    )
    assert second is None or second.id != "dead"


def test_no_eligible_route_raises(tmp_path):
    missing = _local_route(str(tmp_path), "ghost", available=False)
    router = Router(routes=[missing])

    with pytest.raises(ValueError, match="no eligible route"):
        router.route()


def test_health_records_outcomes(tmp_path):
    route = _local_route(str(tmp_path), "r")
    router = Router(routes=[route])
    router.report_outcome("r", ok=True)
    router.report_outcome("r", ok=False)

    snap = router.health.snapshot()
    assert snap["r"]["samples"] == 2
    assert snap["r"]["error_rate"] == 0.5


# ---------------------------------------------------------------------------
# Wiring: HTTP chat endpoint retries the fallback route on failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_retries_fallback_route(tmp_path, monkeypatch):
    primary = _local_route(str(tmp_path), "primary")
    backup = _local_route(str(tmp_path), "backup")

    failing_primary = _FakeModel()
    failing_primary.fail_on.add("boom")
    working_backup = _FakeModel()

    # Private Scheduler (function-scoped loop) injected into the router, so this
    # test is isolated from the global singleton other tests also start/stop.
    private = Scheduler(num_workers=2)
    monkeypatch.setattr(chat_module, "scheduler", private)
    private.register_model("primary", failing_primary)
    private.register_model("backup", working_backup)
    monkeypatch.setattr(chat_module, "model", _FakeModel())
    sched_module.model = chat_module.model
    monkeypatch.setattr(chat_module, "router_engine", Router(routes=[primary, backup]))
    await private.start()

    transport = httpx2.ASGITransport(app=app_module.app)
    try:
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer dev-key"},
                json={
                    "model": "primary",
                    "messages": [{"role": "user", "content": "boom"}],
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["choices"][0]["message"]["content"] == "done:boom"
        # The fallback backend served the request.
        assert r.headers.get("x-router-selected") == "backup"
        # The primary route failed -> its model raised, and the request was
        # served by the fallback backend.
        snap = chat_module.router_engine.health.snapshot()
        assert snap["primary"]["error_rate"] > 0
        assert snap["backup"]["error_rate"] == 0
    finally:
        await private.stop()


@pytest.mark.asyncio
async def test_chat_fallback_respects_max_fallbacks(tmp_path, monkeypatch):
    """Fallback retries are bounded by router_max_fallbacks (default 2)."""
    primary = _local_route(str(tmp_path), "primary")
    backup1 = _local_route(str(tmp_path), "backup1")
    backup2 = _local_route(str(tmp_path), "backup2")
    backup3 = _local_route(str(tmp_path), "backup3")

    def _failing():
        m = _FakeModel()
        m.fail_on.add("boom")
        return m

    private = Scheduler(num_workers=1)
    monkeypatch.setattr(chat_module, "scheduler", private)
    for rid, route in [("primary", primary), ("backup1", backup1), ("backup2", backup2), ("backup3", backup3)]:
        private.register_model(rid, _failing())
    monkeypatch.setattr(chat_module, "model", _FakeModel())
    sched_module.model = chat_module.model
    monkeypatch.setattr(
        chat_module, "router_engine", Router(routes=[primary, backup1, backup2, backup3])
    )
    await private.start()

    transport = httpx2.ASGITransport(app=app_module.app)
    try:
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer dev-key"},
                json={"model": "primary", "messages": [{"role": "user", "content": "boom"}]},
            )
        # 4 routes, but only 2 fallbacks allowed -> primary + 2 = 3 attempts, error.
        assert r.status_code == 503
        snap = chat_module.router_engine.health.snapshot()
        # Primary failed and both fallbacks used; backup3 must NOT have been tried.
        assert "primary" in snap
        assert "backup1" in snap
        assert "backup2" in snap
        assert "backup3" not in snap
    finally:
        await private.stop()


@pytest.mark.asyncio
async def test_chat_no_eligible_route_returns_404(tmp_path, monkeypatch):
    """A request whose only route is missing must not hang or 500."""
    missing = _local_route(str(tmp_path), "ghost", available=False)

    private = Scheduler(num_workers=1)
    monkeypatch.setattr(chat_module, "scheduler", private)
    monkeypatch.setattr(chat_module, "model", _FakeModel())
    sched_module.model = chat_module.model
    monkeypatch.setattr(chat_module, "router_engine", Router(routes=[missing]))
    await private.start()

    transport = httpx2.ASGITransport(app=app_module.app)
    try:
        async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer dev-key"},
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
        assert r.status_code == 404
    finally:
        await private.stop()