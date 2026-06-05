from dataclasses import dataclass


@dataclass(frozen=True)
class UsageSnapshot:
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class BillingService:
    def estimate_usage(self, tokens_in: int, tokens_out: int, rate_per_million: float) -> UsageSnapshot:
        total_tokens = tokens_in + tokens_out
        cost = (total_tokens / 1_000_000.0) * rate_per_million
        return UsageSnapshot(tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)

