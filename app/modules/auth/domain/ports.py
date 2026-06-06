from abc import ABC, abstractmethod

from modules.auth.domain.entities import User

from modules.auth.domain.entities import User


class UserRepositoryPort(ABC):

    @abstractmethod
    def save(self, user: User) -> User:
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> User | None:
        pass

    @abstractmethod
    def find_by_id(self, user_id: str) -> User | None:
        pass


class PasswordHasher(ABC):

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        pass

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        pass


class TokenProvider(ABC):

    @abstractmethod
    def generate(self, payload: dict) -> str:
        pass

    @abstractmethod
    def decode(self, token: str) -> dict:
        pass
