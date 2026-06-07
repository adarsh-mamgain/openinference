from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.db import postgres_connection, postgres_cursor
from app.models.control import ApiKeyRecord


class ApiKeyRepository(Protocol):
    def create(self, api_key: ApiKeyRecord) -> ApiKeyRecord: ...

    def get_by_id(self, key_id: str) -> ApiKeyRecord | None: ...

    def get_by_hash(self, key_hash: str) -> ApiKeyRecord | None: ...

    def list_for_user(self, user_id: str) -> list[ApiKeyRecord]: ...

    def revoke(self, key_id: str) -> ApiKeyRecord | None: ...

    def touch_last_used(self, key_id: str) -> ApiKeyRecord | None: ...


@dataclass
class InMemoryApiKeyRepository:
    keys_by_id: dict[str, ApiKeyRecord] = field(default_factory=dict)
    key_ids_by_hash: dict[str, str] = field(default_factory=dict)

    def create(self, api_key: ApiKeyRecord) -> ApiKeyRecord:
        self.keys_by_id[api_key.id] = api_key
        self.key_ids_by_hash[api_key.key_hash] = api_key.id
        return api_key

    def get_by_id(self, key_id: str) -> ApiKeyRecord | None:
        return self.keys_by_id.get(key_id)

    def get_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        key_id = self.key_ids_by_hash.get(key_hash)
        if not key_id:
            return None
        return self.keys_by_id.get(key_id)

    def list_for_user(self, user_id: str) -> list[ApiKeyRecord]:
        return [record for record in self.keys_by_id.values() if record.user_id == user_id]

    def revoke(self, key_id: str) -> ApiKeyRecord | None:
        api_key = self.keys_by_id.get(key_id)
        if api_key is None:
            return None
        revoked = ApiKeyRecord(
            id=api_key.id,
            user_id=api_key.user_id,
            name=api_key.name,
            prefix=api_key.prefix,
            key_hash=api_key.key_hash,
            active=False,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            revoked_at=datetime.now(timezone.utc),
        )
        self.keys_by_id[key_id] = revoked
        return revoked

    def touch_last_used(self, key_id: str) -> ApiKeyRecord | None:
        api_key = self.keys_by_id.get(key_id)
        if api_key is None:
            return None
        updated = ApiKeyRecord(
            id=api_key.id,
            user_id=api_key.user_id,
            name=api_key.name,
            prefix=api_key.prefix,
            key_hash=api_key.key_hash,
            active=api_key.active,
            created_at=api_key.created_at,
            last_used_at=datetime.now(timezone.utc),
            revoked_at=api_key.revoked_at,
        )
        self.keys_by_id[key_id] = updated
        return updated


@dataclass
class PostgresApiKeyRepository:
    def create(self, api_key: ApiKeyRecord) -> ApiKeyRecord:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO api_keys (id, user_id, name, prefix, key_hash, active, created_at, last_used_at, revoked_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id::text, user_id::text, name, prefix, key_hash, active, created_at, last_used_at, revoked_at
                ''',
                (
                    api_key.id,
                    api_key.user_id,
                    api_key.name,
                    api_key.prefix,
                    api_key.key_hash,
                    api_key.active,
                    api_key.created_at,
                    api_key.last_used_at,
                    api_key.revoked_at,
                ),
            )
            return _row_to_api_key(cursor.fetchone())

    def get_by_id(self, key_id: str) -> ApiKeyRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT id::text, user_id::text, name, prefix, key_hash, active, created_at, last_used_at, revoked_at
                FROM api_keys
                WHERE id = %s
                ''',
                (key_id,),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_api_key(row)

    def get_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT id::text, user_id::text, name, prefix, key_hash, active, created_at, last_used_at, revoked_at
                FROM api_keys
                WHERE key_hash = %s
                ''',
                (key_hash,),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_api_key(row)

    def list_for_user(self, user_id: str) -> list[ApiKeyRecord]:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT id::text, user_id::text, name, prefix, key_hash, active, created_at, last_used_at, revoked_at
                FROM api_keys
                WHERE user_id = %s
                ORDER BY created_at DESC
                ''',
                (user_id,),
            )
            return [_row_to_api_key(row) for row in cursor.fetchall()]

    def revoke(self, key_id: str) -> ApiKeyRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                UPDATE api_keys
                SET active = FALSE,
                    revoked_at = NOW()
                WHERE id = %s
                RETURNING id::text, user_id::text, name, prefix, key_hash, active, created_at, last_used_at, revoked_at
                ''',
                (key_id,),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_api_key(row)

    def touch_last_used(self, key_id: str) -> ApiKeyRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                UPDATE api_keys
                SET last_used_at = NOW()
                WHERE id = %s
                RETURNING id::text, user_id::text, name, prefix, key_hash, active, created_at, last_used_at, revoked_at
                ''',
                (key_id,),
            )
            row = cursor.fetchone()
            return None if row is None else _row_to_api_key(row)


def _row_to_api_key(row) -> ApiKeyRecord:
    return ApiKeyRecord(
        id=row['id'],
        user_id=row['user_id'],
        name=row['name'],
        prefix=row['prefix'],
        key_hash=row['key_hash'],
        active=row['active'],
        created_at=row['created_at'],
        last_used_at=row['last_used_at'],
        revoked_at=row['revoked_at'],
    )


def build_api_key_repository() -> ApiKeyRepository:
    try:
        with postgres_connection():
            pass
    except Exception:
        return InMemoryApiKeyRepository()
    return PostgresApiKeyRepository()
