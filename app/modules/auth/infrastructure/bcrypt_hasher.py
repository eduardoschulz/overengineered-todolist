import bcrypt

from modules.auth.domain.ports import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
