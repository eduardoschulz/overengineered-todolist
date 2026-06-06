from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from modules.auth.application.use_cases import LoginUseCase, RegisterUserUseCase
from modules.auth.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from modules.auth.infrastructure.bcrypt_hasher import BcryptPasswordHasher
from modules.auth.infrastructure.jwt_provider import PyJWTTokenProvider
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository
from modules.auth.interface.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from shared.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    repo = SQLAlchemyUserRepository(db)
    hasher = BcryptPasswordHasher()
    use_case = RegisterUserUseCase(repo=repo, hasher=hasher)

    try:
        user = use_case.execute(email=body.email, password=body.password)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Email already registered")

    return UserResponse(
        id=user.id,
        email=user.email.address,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    repo = SQLAlchemyUserRepository(db)
    hasher = BcryptPasswordHasher()
    token_provider = PyJWTTokenProvider()
    use_case = LoginUseCase(repo=repo, hasher=hasher, token_provider=token_provider)

    try:
        token = use_case.execute(email=body.email, password=body.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(access_token=token)
