from dataclasses import dataclass
from typing import Any


@dataclass
class CacheSettings:
    enabled: bool = True
    ttl_seconds: int = 300


class CacheBackend:
    def __init__(self) -> None:
        self._memory: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self._memory.get(key)

    def set(self, key: str, value: Any) -> None:
        self._memory[key] = value

