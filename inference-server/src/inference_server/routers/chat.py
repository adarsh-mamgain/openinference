"""Router implementing `POST /v1/chat/completions`."""

import time
import uuid

from fastapi import APIRouter

from inference_server.mock_model import count_tokens, generate
from inference_server.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    Usage,
)

router = APIRouter()


@router.post("/chat/completions", response_model=ChatCompletionResponse)
def create_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """Create a chat completion. Mirrors the OpenAI endpoint shape."""
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
