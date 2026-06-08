import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../app"))

import uuid
import pytest
from modules.todo.application.use_cases import (
    CreateTodoListUseCase,
    GetUserTodoListsUseCase,
    AddTodoItemUseCase,
    CompleteTodoItemUseCase,
    DeleteTodoListUseCase,
    PermissionDeniedError,
)


# --- Simple data classes ---

class TodoItem:
    def __init__(self, item_id, list_id, content):
        self.item_id = item_id
        self.list_id = list_id
        self.content = content
        self.completed = False


class TodoList:
    def __init__(self, list_id, owner_id, title):
        self.list_id = list_id
        self.owner_id = owner_id
        self.title = title
        self.items = []


# --- In-memory fake repository ---

class InMemoryTodoRepo:

    def __init__(self):
        self._lists = {}
        self._items = {}

    def create_list(self, user_id: str, title: str) -> TodoList:
        list_id = str(uuid.uuid4())
        todo_list = TodoList(list_id=list_id, owner_id=user_id, title=title)
        self._lists[list_id] = todo_list
        return todo_list

    def find_lists_by_user(self, user_id: str):
        return [l for l in self._lists.values() if l.owner_id == user_id]

    def find_list_by_id(self, list_id: str):
        return self._lists.get(list_id)

    def add_item(self, list_id: str, content: str) -> TodoItem:
        item_id = str(uuid.uuid4())
        item = TodoItem(item_id=item_id, list_id=list_id, content=content)
        self._items[item_id] = item
        self._lists[list_id].items.append(item)
        return item

    def complete_item(self, item_id: str) -> TodoItem:
        item = self._items[item_id]
        item.completed = True
        return item

    def reopen_item(self, item_id: str) -> TodoItem:
        item = self._items[item_id]
        item.completed = False
        return item

    def rename_item(self, item_id: str, new_content: str) -> TodoItem:
        item = self._items[item_id]
        item.content = new_content
        return item

    def delete_list(self, list_id: str) -> None:
        del self._lists[list_id]


# --- Tests ---

def make_repo():
    return InMemoryTodoRepo()


def test_create_list():
    repo = make_repo()
    use_case = CreateTodoListUseCase(repo)
    todo_list = use_case.execute(user_id="user-1", title="My List")
    assert todo_list.title == "My List"
    assert todo_list.owner_id == "user-1"


def test_get_lists_returns_only_own_lists():
    repo = make_repo()
    CreateTodoListUseCase(repo).execute(user_id="user-1", title="List A")
    CreateTodoListUseCase(repo).execute(user_id="user-2", title="List B")
    lists = GetUserTodoListsUseCase(repo).execute(user_id="user-1")
    assert len(lists) == 1
    assert lists[0].title == "List A"


def test_add_item_to_list():
    repo = make_repo()
    todo_list = CreateTodoListUseCase(repo).execute(user_id="user-1", title="My List")
    item = AddTodoItemUseCase(repo).execute(
        user_id="user-1", list_id=todo_list.list_id, content="Buy milk"
    )
    assert item.content == "Buy milk"
    assert item.completed is False


def test_add_item_wrong_owner_raises_error():
    repo = make_repo()
    todo_list = CreateTodoListUseCase(repo).execute(user_id="user-1", title="My List")
    with pytest.raises(PermissionDeniedError):
        AddTodoItemUseCase(repo).execute(
            user_id="user-2", list_id=todo_list.list_id, content="Buy milk"
        )


def test_complete_item():
    repo = make_repo()
    todo_list = CreateTodoListUseCase(repo).execute(user_id="user-1", title="My List")
    item = AddTodoItemUseCase(repo).execute(
        user_id="user-1", list_id=todo_list.list_id, content="Buy milk"
    )
    completed = CompleteTodoItemUseCase(repo).execute(
        user_id="user-1", list_id=todo_list.list_id, item_id=item.item_id
    )
    assert completed.completed is True


def test_delete_list():
    repo = make_repo()
    todo_list = CreateTodoListUseCase(repo).execute(user_id="user-1", title="My List")
    DeleteTodoListUseCase(repo).execute(user_id="user-1", list_id=todo_list.list_id)
    assert repo.find_list_by_id(todo_list.list_id) is None


def test_delete_list_wrong_owner_raises_error():
    repo = make_repo()
    todo_list = CreateTodoListUseCase(repo).execute(user_id="user-1", title="My List")
    with pytest.raises(PermissionDeniedError):
        DeleteTodoListUseCase(repo).execute(
            user_id="user-2", list_id=todo_list.list_id
        )