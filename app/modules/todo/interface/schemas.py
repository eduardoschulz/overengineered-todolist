from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateListRequest(BaseModel):
    """dados para criar uma nova lista de tarefas."""

    name: str


class AddItemRequest(BaseModel):
    """dados para adicionar um item a uma lista."""

    title: str


class RenameItemRequest(BaseModel):
    """dados para renomear um item."""

    title: str


class TodoItemResponse(BaseModel):
    """representacao de um item de tarefa na resposta da API."""

    id: UUID
    title: str
    is_completed: bool
    created_at: datetime


class TodoListResponse(BaseModel):
    """representacao de uma lista de tarefas na resposta da API."""

    id: UUID
    name: str
    owner_id: str
    created_at: datetime
    items: list[TodoItemResponse]
