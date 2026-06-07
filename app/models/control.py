from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class UserRecord:
    id: str
    email: str
    name: str | None
    password_salt: str
    password_hash: str
    plan: str
    credits_cents: int
    rate_limit_per_minute: int
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SessionRecord:
    token_hash: str
    user_id: str
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ApiKeyRecord:
    id: str
    user_id: str
    name: str
    prefix: str
    key_hash: str
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class UsageRecord:
    user_id: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_cents: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int | None = None
