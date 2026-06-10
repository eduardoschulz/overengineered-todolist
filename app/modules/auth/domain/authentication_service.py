from modules.auth.domain.exceptions import InactiveUserError, InvalidCredentialsError
from modules.auth.domain.ports import PasswordHasher, TokenProvider, UserRepositoryPort


class AuthenticationService:
    """servico de dominio responsavel pela autenticacao de usuarios."""

    def __init__(
        self,
        repo: UserRepositoryPort,
        hasher: PasswordHasher,
        token_provider: TokenProvider,
    ) -> None:
        self._repo = repo
        self._hasher = hasher
        self._token_provider = token_provider

    def authenticate(self, email: str, password: str) -> str:
        """autentica um usuario e retorna um token de acesso."""
        user = self._repo.find_by_email(email)
        if user is None:
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            raise InactiveUserError()

        if not self._hasher.verify(password, user.hashed_password.hash_passwd):
            raise InvalidCredentialsError("Invalid email or password")

        return self._token_provider.generate({"sub": str(user.id)})
