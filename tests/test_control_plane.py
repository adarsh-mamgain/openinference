from datetime import datetime, timezone

from app.models.control import UsageRecord, UserRecord
from app.repositories.api_keys import InMemoryApiKeyRepository
from app.repositories.sessions import InMemorySessionRepository
from app.repositories.users import InMemoryUserRepository
from app.repositories.usage import InMemoryUsageRepository
from app.services.auth import AuthService, AuthenticationError, RegistrationError
from app.services.billing import BillingService
from app.services.rate_limit import InMemoryRateLimiter


def make_auth_service() -> AuthService:
    return AuthService(
        users=InMemoryUserRepository(),
        sessions=InMemorySessionRepository(),
        api_keys=InMemoryApiKeyRepository(),
    )


def test_register_login_and_api_key_flow() -> None:
    auth = make_auth_service()

    user, session_token = auth.register(email='owner@example.com', password='secret', name='Owner')
    assert user.email == 'owner@example.com'
    assert session_token

    logged_in_user, second_session = auth.login(email='owner@example.com', password='secret')
    assert logged_in_user.id == user.id
    assert second_session

    api_key, secret = auth.create_api_key(user_id=user.id, name='Production')
    assert api_key.name == 'Production'
    assert secret.startswith('or_live_')

    authenticated = auth.authenticate_api_key(secret)
    assert authenticated.user.id == user.id
    assert len(auth.list_api_keys(user.id)) == 1


def test_register_rejects_duplicate_email() -> None:
    auth = make_auth_service()
    auth.register(email='owner@example.com', password='secret')

    try:
        auth.register(email='owner@example.com', password='another-secret')
    except RegistrationError:
        assert True
    else:
        assert False, 'expected RegistrationError'


def test_login_rejects_wrong_password() -> None:
    auth = make_auth_service()
    auth.register(email='owner@example.com', password='secret')

    try:
        auth.login(email='owner@example.com', password='wrong')
    except AuthenticationError:
        assert True
    else:
        assert False, 'expected AuthenticationError'


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter(window_seconds=60)

    first = limiter.check('user-1', 1)
    second = limiter.check('user-1', 1)

    assert first.allowed is True
    assert second.allowed is False
    assert second.retry_after_seconds is not None


def test_billing_estimate_uses_model_rate_card() -> None:
    billing = BillingService()
    usage = billing.estimate_usage('deepseek-v4-flash', tokens_in=1_000, tokens_out=1_000)

    assert usage.cost_cents > 0


def test_recent_usage_orders_latest_first() -> None:
    repo = InMemoryUsageRepository()
    repo.create(
        UsageRecord(
            user_id='user-1',
            model='deepseek-v4-flash',
            tokens_in=1,
            tokens_out=2,
            cost_cents=1,
            created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
    )
    repo.create(
        UsageRecord(
            user_id='user-1',
            model='qwen3-32b',
            tokens_in=3,
            tokens_out=4,
            cost_cents=2,
            created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
    )

    records = repo.recent_for_user('user-1', limit=5)

    assert records[0].model == 'qwen3-32b'
    assert records[1].model == 'deepseek-v4-flash'
