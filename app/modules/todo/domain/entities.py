import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from .exceptions import (
    AccessDeniedError,
    AlreadyCompletedError,
    EmptyTitleError,
    NotCompletedError,
    TodoItemNotFoundError,
)
from .value_objects import ListName


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass(kw_only=True)
class TodoItem:
    title: str
    created_by: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    completed: bool = False
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None

    def complete(self):
        if self.completed:
            raise AlreadyCompletedError()
        self.completed = True
        self.status = TaskStatus.DONE
        self.updated_at = datetime.now(UTC)

    def reopen(self):
        if not self.completed:
            raise NotCompletedError()
        self.completed = False
        self.status = TaskStatus.PENDING
        self.updated_at = datetime.now(UTC)

    def rename(self, new_title: str):
        if not new_title.strip():
            raise EmptyTitleError()
        self.title = new_title
        self.updated_at = datetime.now(UTC)

    def update(
        self,
        title: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        assigned_to: str | None = None,
    ):
        if title is not None:
            if not title.strip():
                raise EmptyTitleError()
            self.title = title
        if description is not None:
            self.description = description
        if status is not None:
            self.status = status
            if status == TaskStatus.DONE:
                self.completed = True
            else:
                self.completed = False
        if assigned_to is not None:
            self.assigned_to = assigned_to
        self.updated_at = datetime.now(UTC)

    def verify_ownership(self, user_id: str):
        if self.created_by != user_id:
            raise AccessDeniedError()


@dataclass(kw_only=True)
class TodoList:
    name: ListName
    owner_id: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    items: list[TodoItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def _get_item(self, item_id: uuid.UUID) -> TodoItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise TodoItemNotFoundError(str(item_id))

    def add_item(self, title: str) -> TodoItem:
        if not title.strip():
            raise EmptyTitleError()
        item = TodoItem(title=title, created_by=self.owner_id)
        self.items.append(item)
        return item

    def complete_item(self, item_id: uuid.UUID):
        item = self._get_item(item_id)
        item.complete()

    def reopen_item(self, item_id: uuid.UUID):
        item = self._get_item(item_id)
        item.reopen()

    def rename_item(self, item_id: uuid.UUID, new_title: str):
        item = self._get_item(item_id)
        item.rename(new_title)

    def remove_item(self, item_id: uuid.UUID):
        item = self._get_item(item_id)
        self.items.remove(item)

    def verify_ownership(self, user_id: str):
        if self.owner_id != user_id:
            raise AccessDeniedError()
