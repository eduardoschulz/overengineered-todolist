class InvalidTokenError(Exception):
    pass


class TokenExpiredError(InvalidTokenError):
    pass


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass
