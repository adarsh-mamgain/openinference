from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac, sha256
from secrets import token_urlsafe
from uuid import uuid4

from app.models.control import ApiKeyRecord, SessionRecord, UserRecord
from app.repositories.api_keys import ApiKeyRepository
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository


class AuthenticationError(RuntimeError):
    pass


class RegistrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthenticatedUser:
    user: UserRecord
    api_key: ApiKeyRecord | None = None


@dataclass
class AuthService:
    users: UserRepository
    sessions: SessionRepository
    api_keys: ApiKeyRepository
    session_ttl_days: int = 30

    def register(self, *, email: str, password: str, name: str | None = None) -> tuple[UserRecord, str]:
        normalized_email = self._normalize_email(email)
        if self.users.get_by_email(normalized_email) is not None:
            raise RegistrationError('Email already registered')

        salt = self._new_salt()
        user = UserRecord(
            id=str(uuid4()),
            email=normalized_email,
            name=name.strip() if name else None,
            password_salt=salt,
            password_hash=self._hash_password(password, salt),
            plan='free',
            credits_cents=0,
            rate_limit_per_minute=60,
            active=True,
        )
        created_user = self.users.create(user)
        session_token = self._create_session(created_user.id)
        return created_user, session_token

    def login(self, *, email: str, password: str) -> tuple[UserRecord, str]:
        normalized_email = self._normalize_email(email)
        user = self.users.get_by_email(normalized_email)
        if user is None or not user.active:
            raise AuthenticationError('Invalid credentials')
        if not self._verify_password(password, user.password_salt, user.password_hash):
            raise AuthenticationError('Invalid credentials')
        session_token = self._create_session(user.id)
        return user, session_token

    def logout(self, session_token: str) -> None:
        self.sessions.delete_by_token_hash(self._hash_token(session_token))

    def authenticate_session(self, session_token: str) -> UserRecord:
        token_hash = self._hash_token(session_token)
        session = self.sessions.get_by_token_hash(token_hash)
        if session is None:
            raise AuthenticationError('Invalid or expired session')
        user = self.users.get_by_id(session.user_id)
        if user is None or not user.active:
            raise AuthenticationError('Invalid or expired session')
        return user

    def authenticate_api_key(self, api_key: str) -> AuthenticatedUser:
        key_hash = self._hash_token(api_key)
        record = self.api_keys.get_by_hash(key_hash)
        if record is None or not record.active:
            raise AuthenticationError('Invalid API key')
        user = self.users.get_by_id(record.user_id)
        if user is None or not user.active:
            raise AuthenticationError('Invalid API key')
        self.api_keys.touch_last_used(record.id)
        return AuthenticatedUser(user=user, api_key=record)

    def create_api_key(self, *, user_id: str, name: str) -> tuple[ApiKeyRecord, str]:
        prefix = f"or_{token_urlsafe(6)}"
        secret = f"or_live_{token_urlsafe(32)}"
        record = ApiKeyRecord(
            id=str(uuid4()),
            user_id=user_id,
            name=name.strip() or 'Default',
            prefix=prefix,
            key_hash=self._hash_token(secret),
            active=True,
        )
        created = self.api_keys.create(record)
        return created, secret

    def list_api_keys(self, user_id: str) -> list[ApiKeyRecord]:
        return self.api_keys.list_for_user(user_id)

    def revoke_api_key(self, user_id: str, key_id: str) -> ApiKeyRecord:
        record = self.api_keys.get_by_id(key_id)
        if record is None or record.user_id != user_id:
            raise AuthenticationError('API key not found')
        revoked = self.api_keys.revoke(key_id)
        if revoked is None:
            raise AuthenticationError('API key not found')
        return revoked

    def top_up_credits(self, user_id: str, amount_cents: int) -> UserRecord:
        if amount_cents <= 0:
            raise ValueError('amount_cents must be positive')
        updated = self.users.update_credits(user_id, amount_cents)
        if updated is None:
            raise AuthenticationError('User not found')
        return updated

    def debit_credits(self, user_id: str, amount_cents: int) -> UserRecord:
        updated = self.users.update_credits(user_id, -amount_cents)
        if updated is None:
            raise AuthenticationError('User not found')
        return updated

    def _create_session(self, user_id: str) -> str:
        token = token_urlsafe(48)
        session = SessionRecord(
            token_hash=self._hash_token(token),
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.session_ttl_days),
        )
        self.sessions.create(session)
        return token

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().lower()
        if not normalized or '@' not in normalized:
            raise RegistrationError('Invalid email address')
        return normalized

    @staticmethod
    def _new_salt() -> str:
        return token_urlsafe(16)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 120_000).hex()

    @classmethod
    def _verify_password(cls, password: str, salt: str, expected_hash: str) -> bool:
        return cls._hash_password(password, salt) == expected_hash

    @staticmethod
    def _hash_token(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()
