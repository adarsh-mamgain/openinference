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


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AccountResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    plan: str
    credits_cents: int
    rate_limit_per_minute: int
    active: bool = True


class ApiKeyCreateRequest(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    active: bool
    created_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None


class ApiKeyCreatedResponse(BaseModel):
    key: ApiKeyResponse
    secret: str


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


class CheckoutRequest(BaseModel):
    amount_cents: int = Field(ge=100)


class CheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str


class AuthResponse(BaseModel):
    user: AccountResponse


class MessageResponse(BaseModel):
    message: str
