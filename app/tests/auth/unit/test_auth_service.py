import pytest
 
from src.auth.auth_service import AuthenticationService
from src.auth.exceptions import InactiveUserError, InvalidCredentialsError
from src.auth.password_hasher import PasswordHasher
from src.auth.user import User
from src.auth.user_repository import UserRepository
 
 
class PlaintextHasher(PasswordHasher):
    """No-op hasher: stores plain text, compares with ==.
    
    Never use outside tests — the whole point is to avoid bcrypt's cost.
    """
 
    def hash(self, plain: str) -> str:
        return plain  # "hash" is just the plain text itself
 
    def verify(self, plain: str, hashed: str) -> bool:
        return plain == hashed
 
 
class InMemoryUserRepo(UserRepository):
    """Dict-backed repository; no database, no SQLAlchemy session."""
 
    def __init__(self, users: list[User]) -> None:
        self._store: dict[str, User] = {u.username: u for u in users}
 
    def get_by_username(self, username: str) -> User | None:
        return self._store.get(username)
 
 
PLAIN_PASSWORD = "s3cr3t"
 
 
@pytest.fixture()
def hasher() -> PlaintextHasher:
    return PlaintextHasher()
 
 
@pytest.fixture()
def active_user() -> User:
    return User(id=1, username="alice", hashed_password=PLAIN_PASSWORD, is_active=True)
 
 
@pytest.fixture()
def inactive_user() -> User:
    return User(id=2, username="bob", hashed_password=PLAIN_PASSWORD, is_active=False)
 
 
@pytest.fixture()
def service(hasher: PlaintextHasher, active_user: User, inactive_user: User) -> AuthenticationService:
    repo = InMemoryUserRepo([active_user, inactive_user])
    return AuthenticationService(user_repository=repo, password_hasher=hasher)
 
 
 
def test_valid_credentials_do_not_raise(service: AuthenticationService, active_user: User) -> None:
    result = service.authenticate(active_user.username, PLAIN_PASSWORD)
 
    assert result == active_user
 
 
def test_wrong_password_raises_invalid_credentials(
    service: AuthenticationService, active_user: User
) -> None:
    with pytest.raises(InvalidCredentialsError):
        service.authenticate(active_user.username, "wr0ng-p4ssword")
 
 
def test_inactive_user_raises_inactive_user_error(
    service: AuthenticationService, inactive_user: User
) -> None:
    with pytest.raises(InactiveUserError):
        service.authenticate(inactive_user.username, PLAIN_PASSWORD)
