from typing import Optional

import pytest

from modules.todo.application.use_cases import (
    AddTodoItemUseCase,
    CompleteTodoItemUseCase,
    CreateTodoListUseCase,
    DeleteTodoListUseCase,
    GetUserTodoListsUseCase,
)
from modules.todo.domain.entities import TodoList
from modules.todo.domain.exceptions import AccessDeniedError
from modules.todo.domain.ports import TodoListRepositoryPort


class InMemoryTodoRepo(TodoListRepositoryPort):
    def __init__(self):
        self._store: dict[str, TodoList] = {}

    def save(self, todo_list: TodoList) -> TodoList:
        self._store[str(todo_list.id)] = todo_list
        return todo_list

    def find_by_id(self, todo_list_id: str) -> Optional[TodoList]:
        return self._store.get(todo_list_id)

    def find_all_by_owner(self, owner_id: str) -> list[TodoList]:
        return [tl for tl in self._store.values() if tl.owner_id == owner_id]

    def delete(self, todo_list_id: str) -> None:
        self._store.pop(todo_list_id, None)


class TestCreateTodoListUseCase:
    def test_create_list(self):
        repo = InMemoryTodoRepo()
        uc = CreateTodoListUseCase(repo=repo)

        result = uc.execute(name="My List", owner_id="user1")

        assert result.name.value == "My List"
        assert result.owner_id == "user1"
        assert result.id is not None


class TestGetUserTodoListsUseCase:
    def test_get_lists_returns_only_own_lists(self):
        repo = InMemoryTodoRepo()
        uc = CreateTodoListUseCase(repo=repo)
        uc.execute(name="My List", owner_id="user1")
        uc.execute(name="Other List", owner_id="user2")

        get_uc = GetUserTodoListsUseCase(repo=repo)
        user1_lists = get_uc.execute(owner_id="user1")

        assert len(user1_lists) == 1
        assert user1_lists[0].name.value == "My List"


class TestAddTodoItemUseCase:
    def test_add_item_to_list(self):
        repo = InMemoryTodoRepo()
        create_uc = CreateTodoListUseCase(repo=repo)
        todo_list = create_uc.execute(name="My List", owner_id="user1")

        add_uc = AddTodoItemUseCase(repo=repo)
        result = add_uc.execute(
            list_id=str(todo_list.id), title="Buy milk", user_id="user1"
        )

        assert len(result.items) == 1
        assert result.items[0].title == "Buy milk"

    def test_add_item_with_wrong_owner_raises_error(self):
        repo = InMemoryTodoRepo()
        create_uc = CreateTodoListUseCase(repo=repo)
        todo_list = create_uc.execute(name="My List", owner_id="user1")

        add_uc = AddTodoItemUseCase(repo=repo)
        with pytest.raises(AccessDeniedError):
            add_uc.execute(list_id=str(todo_list.id), title="Buy milk", user_id="user2")


class TestCompleteTodoItemUseCase:
    def test_complete_item(self):
        repo = InMemoryTodoRepo()
        create_uc = CreateTodoListUseCase(repo=repo)
        todo_list = create_uc.execute(name="My List", owner_id="user1")
        add_uc = AddTodoItemUseCase(repo=repo)
        todo_list = add_uc.execute(
            list_id=str(todo_list.id), title="Buy milk", user_id="user1"
        )

        complete_uc = CompleteTodoItemUseCase(repo=repo)
        result = complete_uc.execute(
            list_id=str(todo_list.id),
            item_id=todo_list.items[0].id,
            user_id="user1",
        )

        assert result.items[0].completed is True


class TestDeleteTodoListUseCase:
    def test_delete_list(self):
        repo = InMemoryTodoRepo()
        create_uc = CreateTodoListUseCase(repo=repo)
        todo_list = create_uc.execute(name="My List", owner_id="user1")

        delete_uc = DeleteTodoListUseCase(repo=repo)
        delete_uc.execute(list_id=str(todo_list.id), user_id="user1")

        assert repo.find_by_id(str(todo_list.id)) is None

    def test_delete_list_with_wrong_owner_raises_error(self):
        repo = InMemoryTodoRepo()
        create_uc = CreateTodoListUseCase(repo=repo)
        todo_list = create_uc.execute(name="My List", owner_id="user1")

        delete_uc = DeleteTodoListUseCase(repo=repo)
        with pytest.raises(AccessDeniedError):
            delete_uc.execute(list_id=str(todo_list.id), user_id="user2")
