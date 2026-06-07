import uuid

from modules.todo.domain.entities import TodoList
from modules.todo.domain.exceptions import AccessDeniedError, TodoListNotFoundError
from modules.todo.domain.ports import TodoListRepositoryPort
from modules.todo.domain.value_objects import ListName


class CreateTodoListUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, name: str, owner_id: str) -> TodoList:
        todo_list = TodoList(name=ListName(name), owner_id=owner_id)
        return self._repo.save(todo_list)


class GetUserTodoListsUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, owner_id: str) -> list[TodoList]:
        return self._repo.find_all_by_owner(owner_id)


class AddTodoItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, title: str, user_id: str) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        todo_list.add_item(title)
        return self._repo.save(todo_list)

    def _get_list_or_raise(self, list_id: str) -> TodoList:
        todo_list = self._repo.find_by_id(list_id)
        if todo_list is None:
            raise TodoListNotFoundError(list_id)
        return todo_list


class CompleteTodoItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, item_id: uuid.UUID, user_id: str) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        todo_list.complete_item(item_id)
        return self._repo.save(todo_list)

    def _get_list_or_raise(self, list_id: str) -> TodoList:
        todo_list = self._repo.find_by_id(list_id)
        if todo_list is None:
            raise TodoListNotFoundError(list_id)
        return todo_list


class ReopenTodoItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, item_id: uuid.UUID, user_id: str) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        todo_list.reopen_item(item_id)
        return self._repo.save(todo_list)

    def _get_list_or_raise(self, list_id: str) -> TodoList:
        todo_list = self._repo.find_by_id(list_id)
        if todo_list is None:
            raise TodoListNotFoundError(list_id)
        return todo_list


class RenameItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(
        self, list_id: str, item_id: uuid.UUID, new_title: str, user_id: str
    ) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        todo_list.rename_item(item_id, new_title)
        return self._repo.save(todo_list)

    def _get_list_or_raise(self, list_id: str) -> TodoList:
        todo_list = self._repo.find_by_id(list_id)
        if todo_list is None:
            raise TodoListNotFoundError(list_id)
        return todo_list


class DeleteTodoListUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, user_id: str) -> None:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        self._repo.delete(list_id)

    def _get_list_or_raise(self, list_id: str) -> TodoList:
        todo_list = self._repo.find_by_id(list_id)
        if todo_list is None:
            raise TodoListNotFoundError(list_id)
        return todo_list
