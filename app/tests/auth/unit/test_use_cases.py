import uuid
from typing import Optional

from modules.auth.application.use_cases import LoginUseCase, RegisterUserUseCase
from modules.auth.domain.entities import User
from modules.auth.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from modules.auth.domain.ports import PasswordHasher, TokenProvider, UserRepositoryPort
from modules.auth.domain.value_objects import EmailAddress, HashedPassword


class InMemoryUserRepo(UserRepositoryPort):
    def __init__(self):
        self._users: dict[str, dict] = {}

    def save(self, user: User) -> User:
        self._users[str(user.id)] = {
            "id": str(user.id),
            "email": user.email.address,
            "hashed_password": user.hashed_password.hash_passwd,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        return user

    def find_by_email(self, email: str) -> Optional[User]:
        for data in self._users.values():
            if data["email"] == email:
                return User(
                    id=uuid.UUID(data["id"]),
                    email=EmailAddress(data["email"]),
                    hashed_password=HashedPassword(data["hashed_password"]),
                    is_active=data["is_active"],
                    created_at=data["created_at"],
                )
        return None

    def find_by_id(self, user_id: str) -> Optional[User]:
        data = self._users.get(user_id)
        if data is None:
            return None
        return User(
            id=uuid.UUID(data["id"]),
            email=EmailAddress(data["email"]),
            hashed_password=HashedPassword(data["hashed_password"]),
            is_active=data["is_active"],
            created_at=data["created_at"],
        )


class FakeHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return f"hashed:{plain_password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed:{plain_password}"


class FakeTokenProvider(TokenProvider):
    def generate(self, payload: dict) -> str:
        return f"token:{payload['sub']}"

    def decode(self, token: str) -> dict:
        return {"sub": token.replace("token:", "")}


class TestRegisterUserUseCase:
    def test_register_creates_user(self):
        repo = InMemoryUserRepo()
        hasher = FakeHasher()
        uc = RegisterUserUseCase(repo=repo, hasher=hasher)

        user = uc.execute(email="test@example.com", password="secret")

        assert user.email.address == "test@example.com"
        assert user.is_active is True
        assert user.id is not None

    def test_register_with_duplicate_email_raises_error(self):
        repo = InMemoryUserRepo()
        hasher = FakeHasher()
        uc = RegisterUserUseCase(repo=repo, hasher=hasher)

        uc.execute(email="test@example.com", password="secret")

        import pytest

        with pytest.raises(EmailAlreadyExistsError):
            uc.execute(email="test@example.com", password="other")

    def test_register_hashes_the_password(self):
        repo = InMemoryUserRepo()
        hasher = FakeHasher()
        uc = RegisterUserUseCase(repo=repo, hasher=hasher)

        user = uc.execute(email="test@example.com", password="secret")

        assert user.hashed_password.hash_passwd == "hashed:secret"


class TestLoginUseCase:
    def test_login_returns_token(self):
        repo = InMemoryUserRepo()
        hasher = FakeHasher()
        token_provider = FakeTokenProvider()
        register = RegisterUserUseCase(repo=repo, hasher=hasher)
        login = LoginUseCase(repo=repo, hasher=hasher, token_provider=token_provider)

        register.execute(email="test@example.com", password="secret")
        token = login.execute(email="test@example.com", password="secret")

        assert token.startswith("token:")

    def test_login_with_wrong_password_raises_error(self):
        repo = InMemoryUserRepo()
        hasher = FakeHasher()
        token_provider = FakeTokenProvider()
        register = RegisterUserUseCase(repo=repo, hasher=hasher)
        login = LoginUseCase(repo=repo, hasher=hasher, token_provider=token_provider)

        register.execute(email="test@example.com", password="secret")

        import pytest

        with pytest.raises(InvalidCredentialsError):
            login.execute(email="test@example.com", password="wrong")

    def test_login_with_unknown_email_raises_error(self):
        repo = InMemoryUserRepo()
        hasher = FakeHasher()
        token_provider = FakeTokenProvider()
        login = LoginUseCase(repo=repo, hasher=hasher, token_provider=token_provider)

        import pytest

        with pytest.raises(InvalidCredentialsError):
            login.execute(email="unknown@example.com", password="secret")
