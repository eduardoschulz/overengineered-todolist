import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .exceptions import (
    AccessDeniedError,
    AlreadyCompletedError,
    EmptyTitleError,
    NotCompletedError,
    TodoItemNotFoundError,
)
from .value_objects import ListName


@dataclass(kw_only=True)
class TodoItem:
    title: str
    completed: bool = False
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def complete(self):
        if self.completed:
            raise AlreadyCompletedError()
        self.completed = True

    def reopen(self):
        if not self.completed:
            raise NotCompletedError()
        self.completed = False

    def rename(self, new_title: str):
        if not new_title.strip():
            raise EmptyTitleError()
        self.title = new_title


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
        item = TodoItem(title=title)
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
