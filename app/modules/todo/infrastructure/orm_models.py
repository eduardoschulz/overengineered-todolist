import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.base_model import Base


class TodoListORM(Base):
    """modelo ORM para a tabela 'todo_lists' no banco de dados."""

    __tablename__ = "todo_lists"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    items: Mapped[list["TodoItemORM"]] = relationship(
        "TodoItemORM", back_populates="todo_list", cascade="all, delete-orphan"
    )


class TodoItemORM(Base):
    """modelo ORM para a tabela 'todo_items' no banco de dados."""

    __tablename__ = "todo_items"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    todo_list_id: Mapped[str] = mapped_column(
        String, ForeignKey("todo_lists.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    todo_list: Mapped["TodoListORM"] = relationship(
        "TodoListORM", back_populates="items"
    )
