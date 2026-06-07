import uuid

import pytest

from modules.todo.domain.entities import TodoList
from modules.todo.domain.exceptions import (
    AccessDeniedError,
    AlreadyCompletedError,
    EmptyTitleError,
    NotCompletedError,
    TodoItemNotFoundError,
)
from modules.todo.domain.value_objects import ListName


class TestTodoListAggregate:
    def test_add_item_creates_item(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        assert item.title == "Buy milk"
        assert item.id is not None
        assert item in todo_list.items

    def test_add_item_with_empty_title_raises_error(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        with pytest.raises(EmptyTitleError):
            todo_list.add_item("")

    def test_complete_item(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        todo_list.complete_item(item.id)
        assert item.completed is True

    def test_complete_already_completed_raises_error(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        todo_list.complete_item(item.id)
        with pytest.raises(AlreadyCompletedError):
            todo_list.complete_item(item.id)

    def test_reopen_item(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        todo_list.complete_item(item.id)
        todo_list.reopen_item(item.id)
        assert item.completed is False

    def test_reopen_not_completed_raises_error(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        with pytest.raises(NotCompletedError):
            todo_list.reopen_item(item.id)

    def test_rename_item(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        todo_list.rename_item(item.id, "Buy bread")
        assert item.title == "Buy bread"

    def test_rename_with_empty_title_raises_error(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        with pytest.raises(EmptyTitleError):
            todo_list.rename_item(item.id, "")

    def test_remove_item(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        item = todo_list.add_item("Buy milk")
        todo_list.remove_item(item.id)
        assert item not in todo_list.items

    def test_non_existent_item_raises_not_found_error(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        fake_id = uuid.uuid4()
        with pytest.raises(TodoItemNotFoundError):
            todo_list.complete_item(fake_id)

    def test_ownership_check_passes_for_owner(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        todo_list.verify_ownership("user1")

    def test_ownership_check_raises_for_non_owner(self):
        todo_list = TodoList(name=ListName("My List"), owner_id="user1")
        with pytest.raises(AccessDeniedError):
            todo_list.verify_ownership("user2")
