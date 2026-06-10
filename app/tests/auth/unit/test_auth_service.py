import uuid
import pytest

from modules.auth.domain.authentication_service import AuthenticationService
from modules.auth.domain.exceptions import InactiveUserError, InvalidCredentialsError
from modules.auth.domain.ports import PasswordHasher, TokenProvider, UserRepositoryPort
from modules.auth.domain.entities import User
from modules.auth.domain.value_objects import EmailAddress, HashedPassword


class PlaintextHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return plain_password

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return plain_password == hashed_password


class DummyTokenProvider(TokenProvider):
    def generate(self, payload: dict) -> str:
        return "dummy-token"

    def decode(self, token: str) -> dict:
        return {}


class InMemoryUserRepo(UserRepositoryPort):
    def __init__(self, users: list[User]) -> None:
        self._store: dict[str, User] = {u.email.address: u for u in users}

    def save(self, user: User) -> User:
        self._store[user.email.address] = user
        return user

    def find_by_email(self, email: str) -> User | None:
        return self._store.get(email)

    def find_by_id(self, user_id: str) -> User | None:
        for u in self._store.values():
            if str(u.id) == user_id:
                return u
        return None


PLAIN_PASSWORD = "s3cr3t"


@pytest.fixture()
def hasher() -> PlaintextHasher:
    return PlaintextHasher()


@pytest.fixture()
def token_provider() -> DummyTokenProvider:
    return DummyTokenProvider()


@pytest.fixture()
def active_user() -> User:
    return User(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email=EmailAddress("alice@example.com"),
        hashed_password=HashedPassword(PLAIN_PASSWORD),
        is_active=True,
    )


@pytest.fixture()
def inactive_user() -> User:
    return User(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email=EmailAddress("bob@example.com"),
        hashed_password=HashedPassword(PLAIN_PASSWORD),
        is_active=False,
    )


@pytest.fixture()
def service(
    hasher: PlaintextHasher,
    token_provider: DummyTokenProvider,
    active_user: User,
    inactive_user: User,
) -> AuthenticationService:
    repo = InMemoryUserRepo([active_user, inactive_user])
    return AuthenticationService(
        repo=repo,
        hasher=hasher,
        token_provider=token_provider,
    )


def test_valid_credentials_do_not_raise(service: AuthenticationService, active_user: User) -> None:
    token = service.authenticate(active_user.email.address, PLAIN_PASSWORD)
    assert token == "dummy-token"


def test_wrong_password_raises_invalid_credentials(
    service: AuthenticationService, active_user: User
) -> None:
    with pytest.raises(InvalidCredentialsError):
        service.authenticate(active_user.email.address, "wr0ng-p4ssword")


def test_inactive_user_raises_inactive_user_error(
    service: AuthenticationService, inactive_user: User
) -> None:
    with pytest.raises(InactiveUserError):
        service.authenticate(inactive_user.email.address, PLAIN_PASSWORD)
