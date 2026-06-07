class TodoListNotFoundError(Exception):
    def __init__(self, list_id: str):
        self.list_id = list_id
        super().__init__(f"TodoList with id {list_id} not found")


class TodoItemNotFoundError(Exception):
    def __init__(self, item_id: str):
        self.item_id = item_id
        super().__init__(f"TodoItem with id {item_id} not found")


class AlreadyCompletedError(Exception):
    pass


class NotCompletedError(Exception):
    pass


class EmptyTitleError(Exception):
    pass


class AccessDeniedError(Exception):
    pass
