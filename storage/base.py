from abc import ABC, abstractmethod


class PersonaStore(ABC):
    @abstractmethod
    def get(self, user_id): ...          # -> dict or None
    @abstractmethod
    def save(self, user): ...            # dict -> None
    @abstractmethod
    def list_all_ids(self): ...          # -> list[str]


class StateStore(ABC):
    @abstractmethod
    def get(self, key): ...              # -> str or None
    @abstractmethod
    def set(self, key, value, ttl_seconds=None): ...
    @abstractmethod
    def delete(self, key): ...
    @abstractmethod
    def incr(self, key): ...             # -> int
