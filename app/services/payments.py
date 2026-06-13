from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from dodopayments import DodoPayments
except Exception:  # pragma: no cover
    DodoPayments = None  # type: ignore[assignment, misc]

from app.settings import SETTINGS

MIN_CREDITS_CENTS = 1000  # $10 minimum


@dataclass
class PaymentService:
    api_key: str
    environment: str = 'test_mode'
    product_id: str = ''

    def _client(self) -> Any:
        if DodoPayments is None:
            raise RuntimeError('dodopayments is not installed')
        return DodoPayments(
            bearer_token=self.api_key,
            environment=self.environment,
        )

    def is_configured(self) -> bool:
        return bool(self.api_key and self.product_id)

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
            raise RuntimeError(
                'Dodo Payments not configured. '
                'Set DODO_PAYMENTS_API_KEY and DODO_PRODUCT_ID in .env'
            )

        client = self._client()

        # ProductItemReqParam supports `amount` override when the product
        # has pay_what_you_want enabled — this lets us do flexible amounts
        # with a single product instead of one product per price point.
        response = client.checkout_sessions.create(
            product_cart=[
                {
                    'product_id': self.product_id,
                    'quantity': 1,
                    'amount': amount_cents,  # cents, overrides product price
                }
            ],
            customer={
                'email': user_email,
                'name': user_name or user_email,
            },
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': user_id,
                'credits_cents': str(amount_cents),
            },
        )

        return {
            'session_id': response.session_id,
            'checkout_url': response.checkout_url or '',
        }


def build_payment_service() -> PaymentService:
    return PaymentService(
        api_key=SETTINGS.dodo_api_key,
        environment=SETTINGS.dodo_environment,
        product_id=getattr(SETTINGS, 'dodo_product_id', ''),
    )
