"""Router implementing `POST /v1/chat/completions`.

Supports both non-streaming (`stream=false`, default) and streaming
(`stream=true`) responses. Streaming uses Server-Sent Events (SSE), matching
the OpenAI wire format so OpenAI client libraries work unchanged.

The model backend is blocking/CPU-bound, so inference runs in a threadpool
(`asyncio.to_thread`) to keep the event loop free for other requests.
"""

import asyncio
import json
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from inference_server.llm import model
from inference_server.mock_model import (
    count_tokens,
    maybe_tool_call,
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
    return await _non_streaming_chat_completion(request)


async def _non_streaming_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
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

    max_tokens = request.max_tokens or 64
    completion_text = await asyncio.to_thread(model.generate, request.messages, max_tokens)
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


def _stream_chat_completion(request: ChatCompletionRequest) -> StreamingResponse:
    """Stream the model's output as token-level SSE chunks."""
    max_tokens = request.max_tokens or 64
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

        # Advance the blocking generator one chunk at a time in a thread.
        # A sentinel value marks the end because StopIteration cannot be
        # raised through an asyncio Future (asyncio.to_thread).
        chunks = iter(model.stream(request.messages, max_tokens))
        while True:
            text = await asyncio.to_thread(_next_or_sentinel, chunks)
            if text is None:
                break
            payload = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {"index": 0, "delta": {"content": text}, "finish_reason": None}
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


def _next_or_sentinel(iterator):
    """Return the next item or None when the iterator is exhausted."""
    try:
        return next(iterator)
    except StopIteration:
        return None


def _sse_format(data: dict) -> str:
    """Serialize a chunk into the `data: <json>` SSE wire format."""
    return f"data: {json.dumps(data)}\n\n"
