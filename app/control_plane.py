from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.models.control import UserRecord
from app.repositories.users import InMemoryUserRepository, build_user_repository
from app.repositories.usage import InMemoryUsageRepository, build_usage_repository
from app.services.auth import AuthService
from app.services.billing import BillingService
from app.services.rate_limit import InMemoryRateLimiter
from app.settings import SETTINGS


@dataclass
class ControlPlane:
    auth: AuthService
    billing: BillingService
    rate_limiter: InMemoryRateLimiter
    users: object
    usage: object

    @staticmethod
    def build() -> 'ControlPlane':
        users = build_user_repository()
        usage = build_usage_repository()

        if isinstance(users, InMemoryUserRepository) and SETTINGS.dev_api_key:
            users.seed(
                UserRecord(
                    id='dev-user',
                    api_key_fingerprint=sha256(SETTINGS.dev_api_key.encode('utf-8')).hexdigest(),
                    plan='dev',
                    credits_cents=SETTINGS.default_credits_cents,
                    rate_limit_per_minute=SETTINGS.default_rate_limit_per_minute,
                    active=True,
                    email=None,
                ),
                SETTINGS.dev_api_key,
            )

        return ControlPlane(
            auth=AuthService(users=users, dev_api_key=SETTINGS.dev_api_key),
            billing=BillingService(),
            rate_limiter=InMemoryRateLimiter(),
            users=users,
            usage=usage,
        )


CONTROL_PLANE = ControlPlane.build()
