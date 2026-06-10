import logging

from modules.auth.domain.entities import User
from modules.auth.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from modules.auth.domain.ports import PasswordHasher, TokenProvider, UserRepositoryPort
from modules.auth.domain.value_objects import EmailAddress, HashedPassword

logger = logging.getLogger(__name__)


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
        result = self._repo.save(user)
        logger.info("user registered: %s", email)
        return result


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


class GetUserUseCase:
    """busca um usuario por id."""

    def __init__(self, repo: UserRepositoryPort) -> None:
        self._repo = repo

    def execute(self, user_id: str) -> User:
        user = self._repo.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user


class UpdateUserUseCase:
    """atualiza email e/ou senha de um usuario."""

    def __init__(self, repo: UserRepositoryPort, hasher: PasswordHasher) -> None:
        self._repo = repo
        self._hasher = hasher

    def execute(
        self, user_id: str, email: str | None = None, password: str | None = None
    ) -> User:
        user = self._repo.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if email is not None:
            existing = self._repo.find_by_email(email)
            if existing and str(existing.id) != user_id:
                raise EmailAlreadyExistsError(f"User with email {email} already exists")
            user.change_email(EmailAddress(email))

        if password is not None:
            hashed = self._hasher.hash(password)
            user.change_password(HashedPassword(hashed))

        result = self._repo.save(user)
        logger.info("user updated: %s", user_id)
        return result


class DeleteUserUseCase:
    """desativa um usuario (soft delete)."""

    def __init__(self, repo: UserRepositoryPort) -> None:
        self._repo = repo

    def execute(self, user_id: str) -> None:
        user = self._repo.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        user.deactivate()
        self._repo.save(user)
        logger.info("user deactivated: %s", user_id)
