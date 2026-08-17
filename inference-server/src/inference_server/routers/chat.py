"""Router implementing `POST /v1/chat/completions`.

Requests are submitted to the scheduler (``scheduler.scheduler.Scheduler``) as
prioritized jobs. The scheduler's worker pool runs the real local model (with
model-driven tool calling for non-streaming jobs, and token-level streaming for
streaming jobs). The route just submits, waits for the result, and formats the
OpenAI-compatible response — the scheduler being an internal layer between the
HTTP API and the model.

A routing layer (``inference_server.router``) picks which served model/backend
should handle each request based on health and client hints, then logs the
decision. When the primary route fails, non-streaming requests are retried on
the next healthy fallback route.
"""

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from inference_server.config import settings
from inference_server.engines import ProviderEngine
from inference_server.exceptions import ModelUnavailableError
from inference_server.llm import get_route_model, model
from inference_server.metrics import metrics
from inference_server.router import RouteHints, Router
from inference_server.router.registry import build_routes
from inference_server.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    Usage,
)
from scheduler.scheduler import scheduler
from scheduler.schemas import AdmissionRejectedError

logger = logging.getLogger(__name__)

router = APIRouter()

CHUNK_DELAY_SECONDS = 0.05

# The set of models/backends this server can route to.
router_engine = Router(routes=build_routes(available_check=lambda: model.available))

# Bind each non-default route to a real model instance (local weights load
# lazily on first use), so the scheduler executes the route that was actually
# selected. The default route is served via the scheduler's fallback to
# ``inference_server.llm.model``, so it is deliberately not registered here.
for _route in router_engine.routes():
    if _route.id == settings.model_identifier:
        continue
    if _route.backend.value == "local" and _route.model_path:
        scheduler.register_model(_route.id, get_route_model(_route.model_path))
    elif _route.backend.value == "provider" and _route.provider_url:
        scheduler.register_model(
            _route.id,
            ProviderEngine(
                _route.provider_url,
                api_key=_route.provider_api_key,
                model=_route.model_identifier,
            ),
        )


@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    raw_response: Response,
) -> ChatCompletionResponse | StreamingResponse:
    """Create a chat completion. Mirrors the OpenAI endpoint shape."""
    has_provider = any(
        route.backend.value == "provider" and route.available()
        for route in router_engine.routes()
    )
    if not model.available and not has_provider:
        raise ModelUnavailableError(
            "No route available. Download the chat model ("
            "`./scripts/download-model.sh`) or configure a provider endpoint."
        )
    hints = _hints_from_headers(http_request)
    try:
        decision = router_engine.route(requested=request.model, hints=hints)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{request.model}' is not available on this server.",
        ) from exc
    logger.info(
        "route %s <- %s (reason: %s)",
        decision.route.id,
        request.model or "auto",
        decision.reason,
    )
    raw_response.headers["x-router-selected"] = decision.route.id
    raw_response.headers["x-router-reason"] = decision.reason
    if request.stream:
        return await _stream_chat_completion(request, decision)
    return await _non_streaming_chat_completion(request, decision, raw_response)


def _hints_from_headers(http_request: Request) -> RouteHints | None:
    """Read optional routing hints from request headers.

    OpenAI clients won't send these; they let a power user steer routing without
    changing the request body schema.
    """
    quality_raw = http_request.headers.get("x-router-quality")
    budget_raw = http_request.headers.get("x-router-latency-budget-ms")
    cost_raw = http_request.headers.get("x-router-cost-sensitivity")

    hints = RouteHints()
    changed = False
    if quality_raw is not None:
        hints.quality = _clamp01(float(quality_raw))
        changed = True
    if budget_raw is not None:
        hints.latency_budget_ms = float(budget_raw)
        changed = True
    if cost_raw is not None:
        hints.cost_sensitivity = _clamp01(float(cost_raw))
        changed = True
    return hints if changed else None


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


async def _submit_job(
    request: ChatCompletionRequest,
    stream: bool,
    model_name: str | None = None,
) -> "Job":
    """Submit a request to the scheduler, translating admission rejection into a 503."""
    try:
        job = await scheduler.submit_chat(
            messages=[m.model_dump(exclude_none=True) for m in request.messages],
            model_name=model_name or request.model,
            max_tokens=request.max_tokens,
            tools=request.tools,
            priority=0,
            stream=stream,
        )
        return job
    except AdmissionRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": "2"},
        ) from exc


async def _non_streaming_chat_completion(
    request: ChatCompletionRequest,
    decision: "RoutingDecision",
    raw_response: Response,
) -> ChatCompletionResponse:
    """Run the request with fallback: on failure, retry the next healthy route.

    Retries are bounded by ``settings.router_max_fallbacks`` so a run of
    failures can't spin the whole route set.
    """
    attempted = [decision.route.id]
    route = decision.route
    fallbacks_used = 0
    while route is not None:
        try:
            job = await _submit_job(request, stream=False, model_name=route.id)
            await job.done.wait()
            completion_text = job.result or ""
            if completion_text.startswith("error:"):
                raise ModelUnavailableError(completion_text)
            router_engine.report_outcome(route.id, ok=True)
            _set_route_headers(raw_response, route.id)
            response = _build_response(request, completion_text)
            _record_tokens(request, response)
            return response
        except ModelUnavailableError:
            router_engine.report_outcome(route.id, ok=False)
            logger.warning("route %s failed, attempting fallback", route.id)
            if fallbacks_used >= settings.router_max_fallbacks:
                logger.error(
                    "exhausted %d fallbacks for model '%s'",
                    settings.router_max_fallbacks,
                    request.model,
                )
                break
            route = _next_fallback(decision, attempted)
            if route is not None:
                attempted.append(route.id)
                fallbacks_used += 1

    raise ModelUnavailableError(
        f"All routes failed for model '{request.model}': {', '.join(attempted)}"
    )


def _set_route_headers(raw_response: Response, route_id: str) -> None:
    """Stamp the actually-served route onto the response for observability."""
    raw_response.headers["x-router-selected"] = route_id


def _scheduler_model_for(model_name: str):
    """Return the model instance bound to a route id (for token counting).

    Falls back to the default ``model`` so token counting always works even for
    models the scheduler resolved via its own defaults.
    """
    registered = getattr(scheduler, "_model_registry", {})
    instance = registered.get(model_name)
    return instance if instance is not None else model


def _next_fallback(decision, attempted: list[str]):
    """Return the next fallback route not yet attempted, or None."""
    for route_id in decision.fallback_order:
        if route_id in attempted:
            continue
        route = router_engine.get(route_id)
        if (
            route is not None
            and route.enabled
            and route.available()
            and router_engine.health.healthy(route_id)
        ):
            return route
    return None


def _build_response(
    request: ChatCompletionRequest, completion_text: str
) -> ChatCompletionResponse:
    token_model = _scheduler_model_for(request.model)
    completion_tokens = token_model.count_tokens(completion_text)
    prompt_tokens = sum(token_model.count_tokens(m.content or "") for m in request.messages)
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                message=Message(role="assistant", content=completion_text),
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


async def _stream_chat_completion(
    request: ChatCompletionRequest, decision: "RoutingDecision"
) -> StreamingResponse:
    """Stream the model's output as token-level SSE chunks."""
    dispatched_at = time.monotonic()
    job = await _submit_job(request, stream=True, model_name=decision.route.id)
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    async def event_generator():
        try:
            # Role announcement chunk, matching OpenAI.
            first = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}
                ],
            }
            yield _sse_format(first)

            emitted_tokens = 0
            prev_token_time = time.monotonic()
            async for delta in scheduler.subscribe_stream(job.id):
                now = time.monotonic()
                if emitted_tokens == 0:
                    metrics.record_ttft(now - dispatched_at)
                else:
                    metrics.record_inter_token(now - prev_token_time)
                emitted_tokens += 1
                prev_token_time = now

                payload = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {"index": 0, "delta": {"content": delta}, "finish_reason": None}
                    ],
                }
                yield _sse_format(payload)
                await asyncio.sleep(CHUNK_DELAY_SECONDS)

            # Final chunk marks the end of generation.
            done = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield _sse_format(done)
            yield "data: [DONE]\n\n"
        finally:
            job_final = scheduler.job(job.id)
            if job_final is not None and job_final.status.value in ("completed", "failed"):
                ok = job_final.status.value == "completed"
                router_engine.report_outcome(decision.route.id, ok=ok)
                if not ok:
                    logger.warning(
                        "streaming job %s on route %s finished %s",
                        job.id,
                        decision.route.id,
                        job_final.status.value,
                    )
            else:
                # Client disconnected (stream cancelled) or unknown: not a
                # backend failure, so don't pollute the route's health score.
                logger.info(
                    "streaming job %s on route %s ended without terminal status",
                    job.id,
                    decision.route.id,
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_format(data: dict) -> str:
    """Serialize a chunk into the `data: <json>` SSE wire format."""
    return f"data: {json.dumps(data)}\n\n"


def _record_tokens(request: ChatCompletionRequest, response: ChatCompletionResponse) -> None:
    """Push token usage from a non-streaming response into the metrics."""
    usage = response.usage
    metrics.record_tokens(usage.prompt_tokens, usage.completion_tokens)
