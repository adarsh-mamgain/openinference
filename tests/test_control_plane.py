from datetime import datetime, timezone

from app.models.control import UsageRecord, UserRecord
from app.repositories.users import InMemoryUserRepository
from app.repositories.usage import InMemoryUsageRepository
from app.services.auth import AuthService, AuthenticationError
from app.services.billing import BillingService
from app.services.rate_limit import InMemoryRateLimiter


def test_authenticate_returns_user() -> None:
    users = InMemoryUserRepository()
    users.seed(
        UserRecord(
            id='user-1',
            api_key_fingerprint='ignored',
            plan='pro',
            credits_cents=500,
            rate_limit_per_minute=10,
            active=True,
        ),
        'test-key',
    )

    auth = AuthService(users=users)
    user = auth.authenticate('test-key')

    assert user.id == 'user-1'
    assert user.plan == 'pro'


def test_authenticate_rejects_invalid_key() -> None:
    auth = AuthService(users=InMemoryUserRepository())

    try:
        auth.authenticate('bad-key')
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
