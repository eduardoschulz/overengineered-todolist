from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from modules.auth.domain.exceptions import InvalidTokenError, TokenExpiredError
from modules.auth.infrastructure.jwt_provider import PyJWTTokenProvider

security = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    token_provider = PyJWTTokenProvider()
    try:
        payload = token_provider.decode(credentials.credentials)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    from shared.token_blocklist import token_blocklist

    if token_blocklist.is_blocked(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
        )

    return UUID(payload["sub"])
