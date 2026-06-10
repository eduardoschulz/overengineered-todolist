from shared.exceptions import AppError
 
 
class UserAlreadyExistsError(AppError):
    def __init__(self, email: str) -> None:
        super().__init__(f"User already exists: {email}")
        self.email = email
 
 
class UserNotFoundError(AppError):
    def __init__(self, email: str) -> None:
        super().__init__(f"User not found: {email}")
        self.email = email
 
 
class InactiveUserError(AppError):
    def __init__(self) -> None:
        super().__init__("User is inactive")

class InvalidTokenError(Exception):
    pass


class TokenExpiredError(InvalidTokenError):
    pass


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass
