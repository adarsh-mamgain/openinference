from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.models.control import UsageRecord


MODEL_RATE_PER_MILLION_CENTS = {
    'deepseek-v4-flash': 20,
    'qwen3-32b': 35,
    'llama-4-scout': 40,
}


@dataclass(frozen=True)
class BillingEstimate:
    tokens_in: int
    tokens_out: int
    cost_cents: int


@dataclass
class BillingService:
    rate_card: dict[str, int] | None = None

    def rate_per_million_cents(self, model: str) -> int:
        return (self.rate_card or MODEL_RATE_PER_MILLION_CENTS).get(model, 25)

    def estimate_usage(self, model: str, tokens_in: int, tokens_out: int) -> BillingEstimate:
        total_tokens = tokens_in + tokens_out
        rate_per_million = Decimal(self.rate_per_million_cents(model))
        cost = (Decimal(total_tokens) / Decimal(1_000_000)) * rate_per_million
        cost_cents = int(cost.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        return BillingEstimate(tokens_in=tokens_in, tokens_out=tokens_out, cost_cents=cost_cents)

    @staticmethod
    def extract_token_usage(response: Any) -> tuple[int, int]:
        usage = response.get('usage', {}) if isinstance(response, dict) else getattr(response, 'usage', {})
        if isinstance(usage, dict):
            return int(usage.get('prompt_tokens', 0) or 0), int(usage.get('completion_tokens', 0) or 0)
        prompt_tokens = int(getattr(usage, 'prompt_tokens', 0) or 0)
        completion_tokens = int(getattr(usage, 'completion_tokens', 0) or 0)
        return prompt_tokens, completion_tokens

    def to_usage_record(self, user_id: str, model: str, response: Any) -> tuple[UsageRecord, BillingEstimate]:
        tokens_in, tokens_out = self.extract_token_usage(response)
        estimate = self.estimate_usage(model=model, tokens_in=tokens_in, tokens_out=tokens_out)
        usage = UsageRecord(
            user_id=user_id,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_cents=estimate.cost_cents,
        )
        return usage, estimate
