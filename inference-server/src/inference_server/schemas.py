"""OpenAI-compatible request and response models.

These mirror the shapes of the real OpenAI API so that any OpenAI client
library can talk to this server without changes.
"""

from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    name: str
    arguments: str  # JSON-encoded string, matching OpenAI


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: FunctionCall


class Message(BaseModel):
    role: str = Field(description="One of: system, user, assistant, tool")
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "qwen2.5-0.5b-instruct"
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


class EmbeddingRequest(BaseModel):
    model: str = "nomic-embed-text-v1.5"
    input: str | list[str]


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: list[float]
    index: int = 0


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingData]
    model: str
    usage: Usage


class Model(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "inference-server"


class ModelList(BaseModel):
    object: str = "list"
    data: list[Model]
