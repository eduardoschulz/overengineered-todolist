class AppError:
    def __init__(self):
        return self


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class AccessDeniedError(AppError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)


class InvalidCredentialsError(AppError):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)


class TokenExpiredError(AppError):
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, status_code=401)


class InvalidTokenError(AppError):
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, status_code=401)
