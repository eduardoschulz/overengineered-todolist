from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.base_model import Base


class UserORM(Base):
    # Modelo ORM para a tabela 'users' no banco de dados.
    # Mapeia os dados do domínio User para persistência relacional.
    # Pertence exclusivamente à camada de infraestrutura.
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # UUID armazenado como string
    email: Mapped[str] = mapped_column(String, unique=True)  # email único do usuário
    hashed_password: Mapped[str] = mapped_column(String)  # hash bcrypt da senha
    is_active: Mapped[bool] = mapped_column(Boolean)  # se o usuário está ativo
    created_at: Mapped[datetime] = mapped_column(DateTime)  # data/hora de criação
