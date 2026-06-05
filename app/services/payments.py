from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

try:
    from dodopayments import AsyncDodoPayments, DodoPayments
except Exception:  # pragma: no cover - optional runtime dependency
    AsyncDodoPayments = None
    DodoPayments = None


@dataclass(frozen=True)
class DodoPaymentSettings:
    api_key: str
    environment: str = 'live_mode'


@dataclass
class PaymentService:
    settings: DodoPaymentSettings

    def sync_client(self) -> Any:
        if DodoPayments is None:
            raise RuntimeError('dodopayments is not installed')
        return DodoPayments(
            bearer_token=self.settings.api_key,
            environment=self.settings.environment,
        )

    def async_client(self) -> Any:
        if AsyncDodoPayments is None:
            raise RuntimeError('dodopayments is not installed')
        return AsyncDodoPayments(
            bearer_token=self.settings.api_key,
            environment=self.settings.environment,
        )

    def is_configured(self) -> bool:
        return bool(self.settings.api_key)


def build_payment_service() -> PaymentService:
    return PaymentService(
        settings=DodoPaymentSettings(
            api_key=os.getenv('DODO_PAYMENTS_API_KEY', ''),
            environment=os.getenv('DODO_PAYMENTS_ENVIRONMENT', 'live_mode'),
        )
    )
