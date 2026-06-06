from datetime import datetime, timedelta, timezone

import jwt

from modules.auth.domain.exceptions import InvalidTokenError, TokenExpiredError
from modules.auth.domain.ports import TokenProvider
from shared.config import settings


class PyJWTTokenProvider(TokenProvider):
    def generate(self, payload: dict) -> str:
        now = datetime.now(timezone.utc)
        payload["iat"] = now
        payload["exp"] = now + timedelta(minutes=settings.JWT_TTL_MINUTES)
        return jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    def decode(self, token: str) -> dict:
        try:
            return jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError
        except jwt.InvalidTokenError:
            raise InvalidTokenError
