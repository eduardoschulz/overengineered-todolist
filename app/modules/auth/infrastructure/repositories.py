import uuid

from sqlalchemy.orm import Session

from modules.auth.domain.entities import User
from modules.auth.domain.ports import UserRepositoryPort
from modules.auth.domain.value_objects import EmailAddress, HashedPassword
from modules.auth.infrastructure.orm_models import UserORM


class SQLAlchemyUserRepository(UserRepositoryPort):

    def __init__(self, session: Session) -> None:
        self.session = session

    # Converte uma entidade de domínio User para o modelo ORM UserORM
    def _to_orm(self, user: User) -> UserORM:
        return UserORM(
            id=str(user.id),
            email=user.email.address,
            hashed_password=user.hashed_password.hash_passwd,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    # Converte um modelo ORM UserORM para a entidade de domínio User
    def _to_domain(self, orm: UserORM) -> User:
        return User(
            id=uuid.UUID(orm.id),
            email=EmailAddress(orm.email),
            hashed_password=HashedPassword(orm.hashed_password),
            is_active=orm.is_active,
            created_at=orm.created_at,
        )

    # Persiste o usuário no banco de dados (insert ou update)
    def save(self, user: User) -> User:
        orm = self._to_orm(user)
        self.session.merge(orm)
        self.session.commit()
        return self._to_domain(orm)

    # Busca um usuário pelo endereço de email
    def find_by_email(self, email: str) -> User | None:
        orm = self.session.query(UserORM).filter_by(email=email).first()
        if orm is None:
            return None
        return self._to_domain(orm)

    # Busca um usuário pelo ID (UUID armazenado como string)
    def find_by_id(self, user_id: str) -> User | None:
        orm = self.session.query(UserORM).get(user_id)
        if orm is None:
            return None
        return self._to_domain(orm)
