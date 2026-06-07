from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any

try:
    from dodopayments import AsyncDodoPayments, DodoPayments
except Exception:  # pragma: no cover - optional runtime dependency
    AsyncDodoPayments = None
    DodoPayments = None

from app.settings import SETTINGS


@dataclass(frozen=True)
class DodoPaymentSettings:
    api_key: str
    environment: str = 'live_mode'
    credit_packs_json: str = '{}'

    def credit_pack_map(self) -> dict[int, str]:
        raw = json.loads(self.credit_packs_json or '{}')
        return {int(amount): product_id for amount, product_id in raw.items()}


@dataclass
class PaymentService:
    settings: DodoPaymentSettings

    def sync_client(self) -> Any:
        if DodoPayments is None:
            raise RuntimeError('dodopayments is not installed')
        return DodoPayments(bearerToken=self.settings.api_key, environment=self.settings.environment)

    def async_client(self) -> Any:
        if AsyncDodoPayments is None:
            raise RuntimeError('dodopayments is not installed')
        return AsyncDodoPayments(bearerToken=self.settings.api_key, environment=self.settings.environment)

    def is_configured(self) -> bool:
        return bool(self.settings.api_key)

    def create_credit_checkout(self, *, user_email: str, user_name: str | None, amount_cents: int, return_url: str, cancel_url: str) -> dict[str, Any]:
        product_id = self._product_id_for_amount(amount_cents)
        if not product_id:
            raise RuntimeError('No Dodo credit product configured for that amount')
        client = self.sync_client()
        payload = {
            'product_cart': [{'product_id': product_id, 'quantity': 1}],
            'customer': {'email': user_email, 'name': user_name},
            'return_url': return_url,
            'cancel_url': cancel_url,
            'metadata': {'credits_cents': amount_cents, 'credit_amount_cents': amount_cents},
        }
        return client.checkoutSessions.create(payload)

    def _product_id_for_amount(self, amount_cents: int) -> str | None:
        return self.settings.credit_pack_map().get(amount_cents)


def build_payment_service() -> PaymentService:
    return PaymentService(
        settings=DodoPaymentSettings(
            api_key=SETTINGS.dodo_api_key,
            environment=SETTINGS.dodo_environment,
            credit_packs_json=SETTINGS.dodo_credit_packs_json,
        )
    )
