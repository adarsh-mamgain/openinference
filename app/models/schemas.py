from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal['ok']
    service: str


class ModelInfo(BaseModel):
    id: str
    owned_by: str = 'openrouter-oss'


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict[str, Any]]
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool | None = False
    user: str | None = None


class AccountResponse(BaseModel):
    id: str
    plan: str
    credits_cents: int
    rate_limit_per_minute: int
    email: str | None = None
    active: bool = True


class UsageItemResponse(BaseModel):
    model: str
    tokens_in: int
    tokens_out: int
    cost_cents: int
    created_at: str


class UsageResponse(BaseModel):
    data: list[UsageItemResponse]
    total_cost_cents: int
    total_tokens: int
