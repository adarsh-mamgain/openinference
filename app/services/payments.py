from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from dodopayments import DodoPayments
except Exception:  # pragma: no cover
    DodoPayments = None  # type: ignore[assignment, misc]

from app.settings import SETTINGS

# Minimum top-up: $10
MIN_CREDITS_CENTS = 1000


@dataclass
class PaymentService:
    api_key: str
    environment: str = 'test_mode'

    def _client(self) -> Any:
        if DodoPayments is None:
            raise RuntimeError('dodopayments is not installed')
        return DodoPayments(
            bearer_token=self.api_key,
            environment=self.environment,
        )

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def create_credit_checkout(
        self,
        *,
        user_email: str,
        user_name: str | None,
        amount_cents: int,
        return_url: str,
        cancel_url: str,
        user_id: str,
    ) -> dict[str, Any]:
        if amount_cents < MIN_CREDITS_CENTS:
            raise ValueError(f'Minimum top-up is ${MIN_CREDITS_CENTS // 100}')

        if not self.is_configured():
            raise RuntimeError('Dodo Payments is not configured (missing DODO_PAYMENTS_API_KEY)')

        client = self._client()

        # Dodo one-time payment — no product ID needed.
        # amount is in cents, currency USD.
        response = client.payments.create(
            billing={
                'city': '',
                'country': 'US',
                'state': '',
                'street': '',
                'zipcode': '',
            },
            customer={
                'email': user_email,
                'name': user_name or user_email,
            },
            product_cart=[
                {
                    'product_id': self._get_or_create_credit_product(),
                    'quantity': 1,
                }
            ],
            payment_link=True,
            return_url=return_url,
            metadata={
                'user_id': user_id,
                'credits_cents': str(amount_cents),
            },
        )

        return {
            'session_id': getattr(response, 'payment_id', '') or response.get('payment_id', ''),
            'checkout_url': getattr(response, 'payment_link', '') or response.get('payment_link', ''),
        }

    def _get_or_create_credit_product(self) -> str:
        """Return the configured credit product ID from env."""
        product_id = getattr(SETTINGS, 'dodo_product_id', '') or ''
        if not product_id:
            raise RuntimeError(
                'DODO_PRODUCT_ID not set. '
                'Create a one-time product in Dodo dashboard and set DODO_PRODUCT_ID in .env'
            )
        return product_id


def build_payment_service() -> PaymentService:
    return PaymentService(
        api_key=SETTINGS.dodo_api_key,
        environment=SETTINGS.dodo_environment,
    )
