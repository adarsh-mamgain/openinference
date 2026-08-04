"""OpenAI-compatible request and response models.

These mirror the shapes of the real OpenAI API so that any OpenAI client
library can talk to this server without changes.
"""

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(description="One of: system, user, assistant, tool")
    content: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "mock-model"
    messages: list[Message]
    temperature: float = 1.0
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
    tools: list[dict] | None = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: Message
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage
