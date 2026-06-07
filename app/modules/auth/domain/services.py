class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class AuthenticationService:

    def __init__(self, password_hasher):
        self.password_hasher = password_hasher

    def verify_credentials(self, user, plain_password: str) -> None:
        if not user.is_active:
            raise InactiveUserError("User account is inactive.")

        if not self.password_hasher.verify(plain_password, user.hashed_password):
            raise InvalidCredentialsError("Invalid credentials.")