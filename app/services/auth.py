from __future__ import annotations

from dataclasses import dataclass

from app.models.control import UserRecord
from app.repositories.users import UserRepository


class AuthenticationError(RuntimeError):
    pass


@dataclass
class AuthService:
    users: UserRepository
    dev_api_key: str = ''

    def authenticate(self, api_key: str) -> UserRecord:
        if self.dev_api_key and api_key == self.dev_api_key:
            user = self.users.get_by_api_key(api_key)
            if user is not None:
                return user

        user = self.users.get_by_api_key(api_key)
        if user is None or not user.active:
            raise AuthenticationError('Invalid API key')
        return user
