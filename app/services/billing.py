from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.models.control import UsageRecord

# ── Rate card ──────────────────────────────────────────────────────────────
# Cents per 1 million tokens (input + output blended).
# Every model in litellm_config.yaml MUST have an entry here.
# Unlisted models fall back to DEFAULT_RATE.

DEFAULT_RATE_CENTS_PER_M = 30  # safe fallback — never zero

MODEL_RATE_PER_MILLION_CENTS: dict[str, int] = {
    # DeepSeek
    'deepseek-v4-flash': 25,
    'deepseek-v4-pro': 80,
    'deepseek-v3': 35,
    # Qwen
    'qwen3-32b': 35,
    'qwen2.5-72b': 40,
    # Llama
    'llama-4-scout': 48,
    'llama-4-maverick': 60,
    'llama-3.3-70b': 45,
    # Mistral
    'mistral-small-3.1': 20,
    'mixtral-8x22b': 55,
    # Gemma
    'gemma-3-27b': 18,
    'gemma-3-12b': 12,
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
        card = self.rate_card or MODEL_RATE_PER_MILLION_CENTS
        rate = card.get(model)
        if rate is None:
            # Log unknown model so ops can add it to the rate card
            import logging
            logging.getLogger(__name__).warning(
                'BillingService: no rate card entry for model=%r, using default=%d',
                model,
                DEFAULT_RATE_CENTS_PER_M,
            )
            return DEFAULT_RATE_CENTS_PER_M
        return rate

    def estimate_usage(self, model: str, tokens_in: int, tokens_out: int) -> BillingEstimate:
        total_tokens = tokens_in + tokens_out
        rate = Decimal(self.rate_per_million_cents(model))
        cost = (Decimal(total_tokens) / Decimal(1_000_000)) * rate
        # Round up to avoid rounding down to 0 for tiny calls — minimum 1 cent
        cost_cents = max(1, int(cost.quantize(Decimal('1'), rounding=ROUND_HALF_UP))) if total_tokens > 0 else 0
        return BillingEstimate(tokens_in=tokens_in, tokens_out=tokens_out, cost_cents=cost_cents)

    @staticmethod
    def extract_token_usage(response: Any) -> tuple[int, int]:
        usage = (
            response.get('usage', {})
            if isinstance(response, dict)
            else getattr(response, 'usage', {})
        )
        if isinstance(usage, dict):
            return (
                int(usage.get('prompt_tokens', 0) or 0),
                int(usage.get('completion_tokens', 0) or 0),
            )
        return (
            int(getattr(usage, 'prompt_tokens', 0) or 0),
            int(getattr(usage, 'completion_tokens', 0) or 0),
        )

    def to_usage_record(
        self, user_id: str, model: str, response: Any
    ) -> tuple[UsageRecord, BillingEstimate]:
        tokens_in, tokens_out = self.extract_token_usage(response)
        estimate = self.estimate_usage(model=model, tokens_in=tokens_in, tokens_out=tokens_out)
        record = UsageRecord(
            user_id=user_id,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_cents=estimate.cost_cents,
        )
        return record, estimate