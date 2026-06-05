from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.db import postgres_connection, postgres_cursor
from app.models.control import UsageRecord


class UsageRepository(Protocol):
    def create(self, usage: UsageRecord) -> None: ...

    def recent_for_user(self, user_id: str, limit: int = 10) -> list[UsageRecord]: ...


@dataclass
class InMemoryUsageRepository:
    records: list[UsageRecord] = field(default_factory=list)

    def create(self, usage: UsageRecord) -> None:
        self.records.append(usage)

    def recent_for_user(self, user_id: str, limit: int = 10) -> list[UsageRecord]:
        filtered = [record for record in self.records if record.user_id == user_id]
        return list(reversed(filtered[-limit:]))


@dataclass
class PostgresUsageRepository:
    def create(self, usage: UsageRecord) -> None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO usage_logs (user_id, model, tokens_in, tokens_out, cost_cents, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    usage.user_id,
                    usage.model,
                    usage.tokens_in,
                    usage.tokens_out,
                    usage.cost_cents,
                    usage.created_at,
                ),
            )

    def recent_for_user(self, user_id: str, limit: int = 10) -> list[UsageRecord]:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT user_id::text, model, tokens_in, tokens_out, cost_cents, created_at
                FROM usage_logs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (user_id, limit),
            )
            rows = cursor.fetchall()
            return [
                UsageRecord(
                    user_id=row['user_id'],
                    model=row['model'],
                    tokens_in=row['tokens_in'],
                    tokens_out=row['tokens_out'],
                    cost_cents=row['cost_cents'],
                    created_at=row['created_at'],
                )
                for row in rows
            ]


def build_usage_repository() -> UsageRepository:
    try:
        with postgres_connection():
            pass
    except Exception:
        return InMemoryUsageRepository()
    return PostgresUsageRepository()
