"""Router implementing `POST /v1/chat/completions`.

Supports both non-streaming (`stream=false`, default) and streaming
(`stream=true`) responses. Streaming uses Server-Sent Events (SSE), matching
the OpenAI wire format so OpenAI client libraries work unchanged.
"""

import asyncio
import json
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from inference_server.mock_model import (
    count_tokens,
    generate,
    maybe_tool_call,
    stream_chunks,
)
from inference_server.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    Usage,
)

router = APIRouter()

CHUNK_DELAY_SECONDS = 0.05


@router.post("/chat/completions", response_model=None)
async def create_chat_completion(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | StreamingResponse:
    """Create a chat completion. Mirrors the OpenAI endpoint shape."""
    if request.stream:
        return _stream_chat_completion(request)
    return _non_streaming_chat_completion(request)


def _non_streaming_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    if request.tools:
        tool_call, finish_reason = maybe_tool_call(request.messages, f"call_{uuid.uuid4().hex[:16]}")
        if tool_call is not None:
            return ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        message=Message(role="assistant", content=None, tool_calls=[tool_call]),
                        finish_reason=finish_reason,
                    )
                ],
                usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

    completion_text, completion_tokens = generate(
        request.messages, max_tokens=request.max_tokens or 64
    )
    prompt_tokens = sum(count_tokens(m.content or "") for m in request.messages)

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


def _stream_chat_completion(request: ChatCompletionRequest) -> StreamingResponse:
    """Stream word-by-word chunks in the OpenAI SSE format."""
    chunks = stream_chunks(request.messages, max_tokens=request.max_tokens or 64)
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

        for chunk in chunks:
            await asyncio.sleep(CHUNK_DELAY_SECONDS)
            payload = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {"index": 0, "delta": {"content": chunk}, "finish_reason": None}
                ],
            }
            yield _sse_format(payload)

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
