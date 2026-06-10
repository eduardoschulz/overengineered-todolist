from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from modules.auth.application.use_cases import (
    DeleteUserUseCase,
    GetUserUseCase,
    RegisterUserUseCase,
    UpdateUserUseCase,
)
from modules.auth.domain.exceptions import (
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from modules.auth.infrastructure.bcrypt_hasher import BcryptPasswordHasher
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository
from modules.auth.interface.schemas import (
    RegisterRequest,
    UpdateUserRequest,
    UserResponse,
)
from shared.database import get_db
from shared.dependencies import get_current_user_id

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    """cria um novo usuario."""
    repo = SQLAlchemyUserRepository(db)
    hasher = BcryptPasswordHasher()
    uc = RegisterUserUseCase(repo=repo, hasher=hasher)
    try:
        user = uc.execute(email=body.email, password=body.password)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Email already registered")
    return UserResponse(
        id=user.id,
        email=user.email.address,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@users_router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    user: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """retorna dados de um usuario especifico."""
    repo = SQLAlchemyUserRepository(db)
    uc = GetUserUseCase(repo=repo)
    try:
        found = uc.execute(user_id=str(user_id))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=found.id,
        email=found.email.address,
        is_active=found.is_active,
        created_at=found.created_at,
    )


@users_router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    user: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """atualiza informacoes do usuario."""
    repo = SQLAlchemyUserRepository(db)
    hasher = BcryptPasswordHasher()
    uc = UpdateUserUseCase(repo=repo, hasher=hasher)
    try:
        updated = uc.execute(
            user_id=str(user_id),
            email=body.email,
            password=body.password,
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Email already registered")
    return UserResponse(
        id=updated.id,
        email=updated.email.address,
        is_active=updated.is_active,
        created_at=updated.created_at,
    )


@users_router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    user: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """remove o usuario (soft delete)."""
    repo = SQLAlchemyUserRepository(db)
    uc = DeleteUserUseCase(repo=repo)
    try:
        uc.execute(user_id=str(user_id))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
