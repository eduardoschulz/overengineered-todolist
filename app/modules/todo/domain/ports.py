from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.todo.domain.entities import TodoList


class TodoListRepositoryPort(ABC):
    @abstractmethod
    def save(self, todo_list: TodoList) -> TodoList:
        pass

    @abstractmethod
    def find_by_id(self, todo_list_id: str) -> TodoList | None:
        pass

    @abstractmethod
    def find_all_by_owner(self, owner_id: str) -> list[TodoList]:
        pass

    @abstractmethod
    def delete(self, todo_list_id: str) -> None:
        pass
