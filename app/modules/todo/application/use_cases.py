import uuid

from modules.todo.domain.entities import TodoItem, TodoList, TaskStatus
from modules.todo.domain.exceptions import TodoItemNotFoundError, TodoListNotFoundError
from modules.todo.domain.ports import TodoItemRepositoryPort, TodoListRepositoryPort
from modules.todo.domain.value_objects import ListName


class CreateTodoListUseCase:
    """cria uma nova lista de tarefas para um usuario."""

    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, name: str, owner_id: str) -> TodoList:
        todo_list = TodoList(name=ListName(name), owner_id=owner_id)
        return self._repo.save(todo_list)


class GetUserTodoListsUseCase:
    """retorna todas as listas de tarefas de um usuario."""

    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, owner_id: str) -> list[TodoList]:
        return self._repo.find_all_by_owner(owner_id)


class AddTodoItemUseCase:
    """adiciona um item a uma lista de tarefas existente."""

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
    """marca um item como concluido."""

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
    """reabre um item que estava concluido."""

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
    """renomeia o titulo de um item da lista."""

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
    """remove uma lista de tarefas."""

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


class CreateTaskUseCase:
    """cria uma nova tarefa."""

    def __init__(self, repo: TodoItemRepositoryPort) -> None:
        self._repo = repo

    def execute(
        self,
        title: str,
        created_by: str,
        description: str = "",
        status: TaskStatus = TaskStatus.PENDING,
        assigned_to: str | None = None,
    ) -> TodoItem:
        task = TodoItem(
            title=title,
            created_by=created_by,
            description=description,
            status=status,
            assigned_to=assigned_to,
        )
        return self._repo.save(task)


class GetTaskUseCase:
    """busca uma tarefa por id."""

    def __init__(self, repo: TodoItemRepositoryPort) -> None:
        self._repo = repo

    def execute(self, task_id: str) -> TodoItem:
        task = self._repo.find_by_id(task_id)
        if task is None:
            raise TodoItemNotFoundError(task_id)
        return task


class ListTasksByAssigneeUseCase:
    """lista tarefas atribuidas a um usuario."""

    def __init__(self, repo: TodoItemRepositoryPort) -> None:
        self._repo = repo

    def execute(self, user_id: str) -> list[TodoItem]:
        return self._repo.find_by_assignee(user_id)


class UpdateTaskUseCase:
    """atualiza uma tarefa (titulo, descricao, status, assigned_to)."""

    def __init__(self, repo: TodoItemRepositoryPort) -> None:
        self._repo = repo

    def execute(
        self,
        task_id: str,
        user_id: str,
        title: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        assigned_to: str | None = None,
    ) -> TodoItem:
        task = self._repo.find_by_id(task_id)
        if task is None:
            raise TodoItemNotFoundError(task_id)
        task.verify_ownership(user_id)
        task.update(
            title=title,
            description=description,
            status=status,
            assigned_to=assigned_to,
        )
        return self._repo.save(task)


class DeleteTaskUseCase:
    """remove uma tarefa."""

    def __init__(self, repo: TodoItemRepositoryPort) -> None:
        self._repo = repo

    def execute(self, task_id: str, user_id: str) -> None:
        task = self._repo.find_by_id(task_id)
        if task is None:
            raise TodoItemNotFoundError(task_id)
        task.verify_ownership(user_id)
        self._repo.delete(task_id)
