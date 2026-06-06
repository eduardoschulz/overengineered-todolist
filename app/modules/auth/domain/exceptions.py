class InvalidTokenError(Exception):
    pass


class TokenExpiredError(InvalidTokenError):
    pass
