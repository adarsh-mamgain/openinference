from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.db import postgres_connection, postgres_cursor
from app.models.control import SessionRecord


class SessionRepository(Protocol):
    def create(self, session: SessionRecord) -> SessionRecord: ...

    def get_by_token_hash(self, token_hash: str) -> SessionRecord | None: ...

    def delete_by_token_hash(self, token_hash: str) -> None: ...


@dataclass
class InMemorySessionRepository:
    sessions_by_token_hash: dict[str, SessionRecord] = field(default_factory=dict)

    def create(self, session: SessionRecord) -> SessionRecord:
        self.sessions_by_token_hash[session.token_hash] = session
        return session

    def get_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        session = self.sessions_by_token_hash.get(token_hash)
        if session is None:
            return None
        if session.expires_at <= datetime.now(session.expires_at.tzinfo):
            self.sessions_by_token_hash.pop(token_hash, None)
            return None
        return session

    def delete_by_token_hash(self, token_hash: str) -> None:
        self.sessions_by_token_hash.pop(token_hash, None)


@dataclass
class PostgresSessionRepository:
    def create(self, session: SessionRecord) -> SessionRecord:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                INSERT INTO sessions (token_hash, user_id, expires_at, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING token_hash, user_id::text, expires_at, created_at
                ''',
                (session.token_hash, session.user_id, session.expires_at, session.created_at),
            )
            row = cursor.fetchone()
            return _row_to_session(row)

    def get_by_token_hash(self, token_hash: str) -> SessionRecord | None:
        with postgres_cursor() as cursor:
            cursor.execute(
                '''
                SELECT token_hash, user_id::text, expires_at, created_at
                FROM sessions
                WHERE token_hash = %s
                ''',
                (token_hash,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            if row['expires_at'] <= datetime.now(row['expires_at'].tzinfo):
                self.delete_by_token_hash(token_hash)
                return None
            return _row_to_session(row)

    def delete_by_token_hash(self, token_hash: str) -> None:
        with postgres_cursor() as cursor:
            cursor.execute('DELETE FROM sessions WHERE token_hash = %s', (token_hash,))


def _row_to_session(row) -> SessionRecord:
    return SessionRecord(
        token_hash=row['token_hash'],
        user_id=row['user_id'],
        expires_at=row['expires_at'],
        created_at=row['created_at'],
    )


def build_session_repository() -> SessionRepository:
    try:
        with postgres_connection():
            pass
    except Exception:
        return InMemorySessionRepository()
    return PostgresSessionRepository()
