from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class UserRecord:
    id: str
    api_key_fingerprint: str
    plan: str
    credits_cents: int
    rate_limit_per_minute: int
    active: bool = True
    email: str | None = None


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
