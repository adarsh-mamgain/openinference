"""Router implementing `POST /v1/chat/completions`.

Requests are submitted to the scheduler (``scheduler.scheduler.Scheduler``) as
prioritized jobs. The scheduler's worker pool runs the real local model (with
model-driven tool calling for non-streaming jobs, and token-level streaming for
streaming jobs). The route just submits, waits for the result, and formats the
OpenAI-compatible response — the scheduler being an internal layer between the
HTTP API and the model.
"""

import asyncio
import json
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from inference_server.exceptions import ModelUnavailableError
from inference_server.llm import model
from inference_server.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    Usage,
)
from scheduler.scheduler import scheduler

router = APIRouter()

CHUNK_DELAY_SECONDS = 0.05


@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | StreamingResponse:
    """Create a chat completion. Mirrors the OpenAI endpoint shape."""
    if not model.available:
        raise ModelUnavailableError(
            "Chat model not downloaded. Run `./scripts/download-model.sh` and restart."
        )
    if request.stream:
        return await _stream_chat_completion(request)
    return await _non_streaming_chat_completion(request)


async def _non_streaming_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    job = await scheduler.submit_chat(
        messages=[m.model_dump(exclude_none=True) for m in request.messages],
        max_tokens=request.max_tokens,
        tools=request.tools,
        priority=0,
    )
    await job.done.wait()

    completion_text = job.result or ""
    if completion_text.startswith("error:"):
        raise ModelUnavailableError(completion_text)

    return _build_response(request, completion_text)


def _build_response(
    request: ChatCompletionRequest, completion_text: str
) -> ChatCompletionResponse:
    completion_tokens = model.count_tokens(completion_text)
    prompt_tokens = sum(model.count_tokens(m.content or "") for m in request.messages)
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


async def _stream_chat_completion(request: ChatCompletionRequest) -> StreamingResponse:
    """Stream the model's output as token-level SSE chunks."""
    job = await scheduler.submit_chat(
        messages=[m.model_dump(exclude_none=True) for m in request.messages],
        max_tokens=request.max_tokens,
        tools=request.tools,
        priority=0,
        stream=True,
    )
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    async def event_generator():
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

        async for delta in scheduler.subscribe_stream(job.id):
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_format(data: dict) -> str:
    """Serialize a chunk into the `data: <json>` SSE wire format."""
    return f"data: {json.dumps(data)}\n\n"
