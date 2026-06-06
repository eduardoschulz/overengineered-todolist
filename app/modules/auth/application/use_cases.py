from modules.auth.domain.entities import User
from modules.auth.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from modules.auth.domain.ports import PasswordHasher, TokenProvider, UserRepositoryPort
from modules.auth.domain.value_objects import EmailAddress, HashedPassword


class RegisterUserUseCase:
    def __init__(
        self,
        repo: UserRepositoryPort,
        hasher: PasswordHasher,
    ) -> None:
        self._repo = repo
        self._hasher = hasher

    def execute(self, email: str, password: str) -> User:
        if self._repo.find_by_email(email):
            raise EmailAlreadyExistsError(f"User with email {email} already exists")

        hashed = self._hasher.hash(password)
        user = User(
            email=EmailAddress(email),
            hashed_password=HashedPassword(hashed),
            is_active=True,
        )
        return self._repo.save(user)


class LoginUseCase:
    def __init__(
        self,
        repo: UserRepositoryPort,
        hasher: PasswordHasher,
        token_provider: TokenProvider,
    ) -> None:
        self._repo = repo
        self._hasher = hasher
        self._token_provider = token_provider

    def execute(self, email: str, password: str) -> str:
        user = self._repo.find_by_email(email)
        if user is None:
            raise InvalidCredentialsError("Invalid email or password")

        if not self._hasher.verify(password, user.hashed_password.hash_passwd):
            raise InvalidCredentialsError("Invalid email or password")

        return self._token_provider.generate({"sub": str(user.id)})
