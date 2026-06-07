from __future__ import annotations

from dataclasses import dataclass

from app.repositories.api_keys import ApiKeyRepository, build_api_key_repository
from app.repositories.sessions import SessionRepository, build_session_repository
from app.repositories.users import InMemoryUserRepository, UserRepository, build_user_repository
from app.repositories.usage import InMemoryUsageRepository, UsageRepository, build_usage_repository
from app.services.auth import AuthService
from app.services.billing import BillingService
from app.services.payments import PaymentService, build_payment_service
from app.services.rate_limit import InMemoryRateLimiter
from app.settings import SETTINGS


@dataclass
class ControlPlane:
    auth: AuthService
    billing: BillingService
    payments: PaymentService
    rate_limiter: InMemoryRateLimiter
    users: UserRepository
    sessions: SessionRepository
    api_keys: ApiKeyRepository
    usage: UsageRepository

    @staticmethod
    def build() -> 'ControlPlane':
        users = build_user_repository()
        sessions = build_session_repository()
        api_keys = build_api_key_repository()
        usage = build_usage_repository()
        auth = AuthService(users=users, sessions=sessions, api_keys=api_keys)

        if SETTINGS.dev_email and SETTINGS.dev_password:
            existing = users.get_by_email(SETTINGS.dev_email)
            if existing is None:
                user, _ = auth.register(email=SETTINGS.dev_email, password=SETTINGS.dev_password, name='Development')
                auth.top_up_credits(user.id, SETTINGS.default_credits_cents)
                users.set_rate_limit(user.id, SETTINGS.default_rate_limit_per_minute)

        return ControlPlane(
            auth=auth,
            billing=BillingService(),
            payments=build_payment_service(),
            rate_limiter=InMemoryRateLimiter(),
            users=users,
            sessions=sessions,
            api_keys=api_keys,
            usage=usage,
        )


CONTROL_PLANE = ControlPlane.build()
