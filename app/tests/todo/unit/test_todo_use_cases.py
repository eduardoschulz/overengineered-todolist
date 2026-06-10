from typing import Optional

import pytest

from modules.todo.application.use_cases import (
    CreateTaskUseCase,
    DeleteTaskUseCase,
    GetTaskUseCase,
    ListTasksByAssigneeUseCase,
    UpdateTaskUseCase,
)
from modules.todo.domain.entities import TaskStatus, TodoItem
from modules.todo.domain.exceptions import AccessDeniedError, TodoItemNotFoundError
from modules.todo.domain.ports import TodoItemRepositoryPort


class InMemoryTaskRepo(TodoItemRepositoryPort):
    def __init__(self):
        self._store: dict[str, TodoItem] = {}

    def save(self, item: TodoItem) -> TodoItem:
        self._store[str(item.id)] = item
        return item

    def find_by_id(self, item_id: str) -> Optional[TodoItem]:
        return self._store.get(item_id)

    def find_by_assignee(self, user_id: str) -> list[TodoItem]:
        return [t for t in self._store.values() if t.assigned_to == user_id]

    def delete(self, item_id: str) -> None:
        self._store.pop(item_id, None)


class TestCreateTaskUseCase:
    def test_create_task_with_defaults(self):
        repo = InMemoryTaskRepo()
        uc = CreateTaskUseCase(repo=repo)

        result = uc.execute(title="Buy milk", created_by="user1")

        assert result.title == "Buy milk"
        assert result.created_by == "user1"
        assert result.status == TaskStatus.PENDING
        assert result.description == ""
        assert result.assigned_to is None

    def test_create_task_with_all_fields(self):
        repo = InMemoryTaskRepo()
        uc = CreateTaskUseCase(repo=repo)

        result = uc.execute(
            title="Review PR",
            created_by="user1",
            description="Check the new feature",
            status=TaskStatus.IN_PROGRESS,
            assigned_to="user2",
        )

        assert result.title == "Review PR"
        assert result.description == "Check the new feature"
        assert result.status == TaskStatus.IN_PROGRESS
        assert result.assigned_to == "user2"


class TestGetTaskUseCase:
    def test_get_task_returns_task(self):
        repo = InMemoryTaskRepo()
        create_uc = CreateTaskUseCase(repo=repo)
        task = create_uc.execute(title="Read book", created_by="user1")

        get_uc = GetTaskUseCase(repo=repo)
        result = get_uc.execute(task_id=str(task.id))

        assert result.title == "Read book"

    def test_get_task_not_found_raises_error(self):
        repo = InMemoryTaskRepo()
        uc = GetTaskUseCase(repo=repo)

        with pytest.raises(TodoItemNotFoundError):
            uc.execute(task_id="nonexistent")


class TestListTasksByAssigneeUseCase:
    def test_list_tasks_by_assignee(self):
        repo = InMemoryTaskRepo()
        create_uc = CreateTaskUseCase(repo=repo)
        create_uc.execute(
            title="Task 1", created_by="user1", assigned_to="user2"
        )
        create_uc.execute(
            title="Task 2", created_by="user1", assigned_to="user2"
        )
        create_uc.execute(
            title="Task 3", created_by="user1", assigned_to="user3"
        )

        uc = ListTasksByAssigneeUseCase(repo=repo)
        results = uc.execute(user_id="user2")

        assert len(results) == 2
        titles = [t.title for t in results]
        assert "Task 1" in titles
        assert "Task 2" in titles


class TestUpdateTaskUseCase:
    def test_update_task_title_and_status(self):
        repo = InMemoryTaskRepo()
        create_uc = CreateTaskUseCase(repo=repo)
        task = create_uc.execute(title="Old title", created_by="user1")

        uc = UpdateTaskUseCase(repo=repo)
        result = uc.execute(
            task_id=str(task.id),
            user_id="user1",
            title="New title",
            status=TaskStatus.DONE,
        )

        assert result.title == "New title"
        assert result.status == TaskStatus.DONE
        assert result.completed is True

    def test_update_task_by_non_owner_raises_error(self):
        repo = InMemoryTaskRepo()
        create_uc = CreateTaskUseCase(repo=repo)
        task = create_uc.execute(title="My task", created_by="user1")

        uc = UpdateTaskUseCase(repo=repo)
        with pytest.raises(AccessDeniedError):
            uc.execute(task_id=str(task.id), user_id="user2", title="Hijacked")


class TestDeleteTaskUseCase:
    def test_delete_task(self):
        repo = InMemoryTaskRepo()
        create_uc = CreateTaskUseCase(repo=repo)
        task = create_uc.execute(title="To delete", created_by="user1")

        uc = DeleteTaskUseCase(repo=repo)
        uc.execute(task_id=str(task.id), user_id="user1")

        assert repo.find_by_id(str(task.id)) is None

    def test_delete_task_by_non_owner_raises_error(self):
        repo = InMemoryTaskRepo()
        create_uc = CreateTaskUseCase(repo=repo)
        task = create_uc.execute(title="My task", created_by="user1")

        uc = DeleteTaskUseCase(repo=repo)
        with pytest.raises(AccessDeniedError):
            uc.execute(task_id=str(task.id), user_id="user2")
