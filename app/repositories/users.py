from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol

from app.db import postgres_connection, postgres_cursor
from app.models.control import UserRecord


class UserRepository(Protocol):
    def create(self, user: UserRecord) -> UserRecord: ...

    def get_by_id(self, user_id: str) -> UserRecord | None: ...

    def get_by_email(self, email: str) -> UserRecord | None: ...

    def update_credits(self, user_id: str, delta_cents: int) -> UserRecord | None: ...

    def set_rate_limit(self, user_id: str, rate_limit_per_minute: int) -> UserRecord | None: ...


@dataclass
class InMemoryUserRepository:
    users_by_id: dict[str, UserRecord] = field(default_factory=dict)
    user_ids_by_email: dict[str, str] = field(default_factory=dict)

    def create(self, user: UserRecord) -> UserRecord:
        self.users_by_id[user.id] = user
        self.user_ids_by_email[user.email.lower()] = user.id
        return user

    def get_by_id(self, user_id: str) -> UserRecord | None:
        return self.users_by_id.get(user_id)

    def get_by_email(self, email: str) -> UserRecord | None:
        user_id = self.user_ids_by_email.get(email.lower())
        if not user_id:
            return None
        return self.users_by_id.get(user_id)

    def update_credits(self, user_id: str, delta_cents: int) -> UserRecord | None:
        user = self.users_by_id.get(user_id)
        if user is None:
            return None
        updated = UserRecord(
            id=user.id,
            email=user.email,
            name=user.name,
            password_salt=user.password_salt,
            password_hash=user.password_hash,
            plan=user.plan,
            credits_cents=user.credits_cents + delta_cents,
            rate_limit_per_minute=user.rate_limit_per_minute,
            active=user.active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self.users_by_id[user_id] = updated
        self.user_ids_by_email[user.email.lower()] = user.id
        return updated

    def set_rate_limit(self, user_id: str, rate_limit_per_minute: int) -> UserRecord | None:
        user = self.users_by_id.get(user_id)
        if user is None:
            return None
        updated = UserRecord(
            id=user.id,
            email=user.email,
            name=user.name,
            password_salt=user.password_salt,
            password_hash=user.password_hash,
            plan=user.plan,
            credits_cents=user.credits_cents,
            rate_limit_per_minute=rate_limit_per_minute,
            active=user.active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self.users_by_id[user_id] = updated
        self.user_ids_by_email[user.email.lower()] = user.id
        return updated


@dataclass
class PostgresUserRepository:
    def create(self, user: UserRecord) -> UserRecord:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO users (id, email, name, password_salt, password_hash, plan, credits_cents, rate_limit_per_minute, active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id::text, email, name, password_salt, password_hash, plan, credits_cents, rate_limit_per_minute, active, created_at, updated_at
                ''',
                (
                    user.id,
                    user.email,
                    user.name,
                    user.password_salt,
                    user.password_hash,
                    user.plan,
                    user.credits_cents,
                    user.rate_limit_per_minute,
                    user.active,
                    user.created_at,
                    user.updated_at,
                ),
            )
            return _row_to_user(cursor.fetchone())

    def get_by_id(self, user_id: str) -> UserRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT id::text, email, name, password_salt, password_hash, plan, credits_cents, rate_limit_per_minute, active, created_at, updated_at
                FROM users
                WHERE id = %s
                ''',
                (user_id,),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_user(row)

    def get_by_email(self, email: str) -> UserRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT id::text, email, name, password_salt, password_hash, plan, credits_cents, rate_limit_per_minute, active, created_at, updated_at
                FROM users
                WHERE LOWER(email) = LOWER(%s)
                ''',
                (email,),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_user(row)

    def update_credits(self, user_id: str, delta_cents: int) -> UserRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                UPDATE users
                SET credits_cents = credits_cents + %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id::text, email, name, password_salt, password_hash, plan, credits_cents, rate_limit_per_minute, active, created_at, updated_at
                ''',
                (delta_cents, user_id),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_user(row)

    def set_rate_limit(self, user_id: str, rate_limit_per_minute: int) -> UserRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                UPDATE users
                SET rate_limit_per_minute = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id::text, email, name, password_salt, password_hash, plan, credits_cents, rate_limit_per_minute, active, created_at, updated_at
                ''',
                (rate_limit_per_minute, user_id),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_user(row)


def _row_to_user(row) -> UserRecord:
    return UserRecord(
        id=row['id'],
        email=row['email'],
        name=row['name'],
        password_salt=row['password_salt'],
        password_hash=row['password_hash'],
        plan=row['plan'],
        credits_cents=row['credits_cents'],
        rate_limit_per_minute=row['rate_limit_per_minute'],
        active=row['active'],
        created_at=row['created_at'],
        updated_at=row['updated_at'],
    )


def build_user_repository() -> UserRepository:
    try:
        with postgres_connection():
            pass
    except Exception:
        return InMemoryUserRepository()
    return PostgresUserRepository()
