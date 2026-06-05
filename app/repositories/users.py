from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol

from app.db import postgres_connection, postgres_cursor
from app.models.control import UserRecord


class UserRepository(Protocol):
    def get_by_api_key(self, api_key: str) -> UserRecord | None: ...

    def adjust_credits(self, user_id: str, delta_cents: int) -> UserRecord | None: ...


@dataclass
class InMemoryUserRepository:
    users_by_fingerprint: dict[str, UserRecord] = field(default_factory=dict)

    def seed(self, user: UserRecord, raw_api_key: str) -> None:
        self.users_by_fingerprint[self._fingerprint(raw_api_key)] = user

    def get_by_api_key(self, api_key: str) -> UserRecord | None:
        return self.users_by_fingerprint.get(self._fingerprint(api_key))

    def adjust_credits(self, user_id: str, delta_cents: int) -> UserRecord | None:
        for fingerprint, user in list(self.users_by_fingerprint.items()):
            if user.id != user_id:
                continue
            updated = UserRecord(
                id=user.id,
                api_key_fingerprint=user.api_key_fingerprint,
                plan=user.plan,
                credits_cents=user.credits_cents + delta_cents,
                rate_limit_per_minute=user.rate_limit_per_minute,
                active=user.active,
                email=user.email,
            )
            self.users_by_fingerprint[fingerprint] = updated
            return updated
        return None

    @staticmethod
    def _fingerprint(api_key: str) -> str:
        return sha256(api_key.encode('utf-8')).hexdigest()


@dataclass
class PostgresUserRepository:
    def get_by_api_key(self, api_key: str) -> UserRecord | None:
        fingerprint = self._fingerprint(api_key)
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT id::text, api_key_fingerprint, plan, credits_cents, rate_limit_per_minute, active, email
                FROM users
                WHERE api_key_fingerprint = %s
                ''',
                (fingerprint,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return UserRecord(
                id=row['id'],
                api_key_fingerprint=row['api_key_fingerprint'],
                plan=row['plan'],
                credits_cents=row['credits_cents'],
                rate_limit_per_minute=row['rate_limit_per_minute'],
                active=row['active'],
                email=row['email'],
            )

    def adjust_credits(self, user_id: str, delta_cents: int) -> UserRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                UPDATE users
                SET credits_cents = credits_cents + %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id::text, api_key_fingerprint, plan, credits_cents, rate_limit_per_minute, active, email
                ''',
                (delta_cents, user_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return UserRecord(
                id=row['id'],
                api_key_fingerprint=row['api_key_fingerprint'],
                plan=row['plan'],
                credits_cents=row['credits_cents'],
                rate_limit_per_minute=row['rate_limit_per_minute'],
                active=row['active'],
                email=row['email'],
            )

    @staticmethod
    def _fingerprint(api_key: str) -> str:
        return sha256(api_key.encode('utf-8')).hexdigest()


def build_user_repository() -> UserRepository:
    try:
        with postgres_connection():
            pass
    except Exception:
        return InMemoryUserRepository()
    return PostgresUserRepository()
