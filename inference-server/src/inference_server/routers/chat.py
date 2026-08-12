"""Router implementing `POST /v1/chat/completions`.

Supports both non-streaming (`stream=false`, default) and streaming
(`stream=true`) responses. Streaming uses Server-Sent Events (SSE), matching
the OpenAI wire format so OpenAI client libraries work unchanged.

The model backend is blocking/CPU-bound, so inference runs in a threadpool
(`asyncio.to_thread`) to keep the event loop free for other requests.

Tool / function calling is fully model-driven: the local model decides when to
emit a tool call (from the registered tools), the tool is executed, its result
is fed back into the conversation, and the model replies. Token usage is
measured with the model's real tokenizer.
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
    ToolCall,
    Usage,
)
from inference_server.tools import (
    TOOL_SCHEMAS,
    parse_text_tool_call,
    run_tool,
    tool_result_message,
)

router = APIRouter()

CHUNK_DELAY_SECONDS = 0.05
MAX_TOOL_TURNS = 4


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
        return _stream_chat_completion(request)
    return await _non_streaming_chat_completion(request)


async def _non_streaming_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    messages = list(request.messages)
    max_tokens = request.max_tokens or 64
    tools = request.tools or TOOL_SCHEMAS

    # Model-driven tool-calling loop: run the model, execute any tool call it
    # emits (structured `tool_calls` or the Qwen `<tool_call>` text format),
    # feed the result back, and repeat until the model answers or we hit the
    # turn budget.
    for _ in range(MAX_TOOL_TURNS):
        content, tool_calls, finish_reason = await asyncio.to_thread(
            model.generate, messages, max_tokens, tools
        )

        if tool_calls:
            for call in tool_calls:
                result = await asyncio.to_thread(run_tool, call)
                messages.append(_as_tool_call_message(call))
                messages.append(tool_result_message(call, result))
            continue

        # The small instruct model renders tool calls as text; recognize them
        # and run the same execution loop.
        text_call = await asyncio.to_thread(parse_text_tool_call, content or "")
        if text_call is not None:
            result = await asyncio.to_thread(run_tool, text_call)
            messages.append(_as_tool_call_message(text_call, content))
            messages.append(tool_result_message(text_call, result))
            continue

        return _build_response(request, content or "", messages)

    raise RuntimeError("Tool-calling loop exceeded its turn budget")


def _as_tool_call_message(call: ToolCall, content: str | None = None) -> Message:
    """Build the assistant message carrying the tool call the model requested."""
    return Message(
        role="assistant",
        content=content,
        tool_calls=[call],
    )


def _build_response(
    request: ChatCompletionRequest, completion_text: str, messages: list[Message]
) -> ChatCompletionResponse:
    completion_tokens = model.count_tokens(completion_text)
    prompt_tokens = model.count_tokens_messages(messages)
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
    tools = request.tools or TOOL_SCHEMAS
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
        chunks = iter(model.stream(request.messages, max_tokens, tools))
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
