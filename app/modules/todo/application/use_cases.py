class PermissionDeniedError(Exception):
    pass


class NotFoundError(Exception):
    pass


class CreateTodoListUseCase:

    def __init__(self, todo_repository):
        self.todo_repository = todo_repository

    def execute(self, user_id: str, title: str):
        todo_list = self.todo_repository.create_list(user_id=user_id, title=title)
        return todo_list


class GetUserTodoListsUseCase:

    def __init__(self, todo_repository):
        self.todo_repository = todo_repository

    def execute(self, user_id: str):
        return self.todo_repository.find_lists_by_user(user_id=user_id)


class AddTodoItemUseCase:

    def __init__(self, todo_repository):
        self.todo_repository = todo_repository

    def execute(self, user_id: str, list_id: str, content: str):
        todo_list = self.todo_repository.find_list_by_id(list_id)
        if todo_list is None:
            raise NotFoundError("Todo list not found.")
        if todo_list.owner_id != user_id:
            raise PermissionDeniedError("You do not own this list.")
        item = self.todo_repository.add_item(list_id=list_id, content=content)
        return item


class CompleteTodoItemUseCase:

    def __init__(self, todo_repository):
        self.todo_repository = todo_repository

    def execute(self, user_id: str, list_id: str, item_id: str):
        todo_list = self.todo_repository.find_list_by_id(list_id)
        if todo_list is None:
            raise NotFoundError("Todo list not found.")
        if todo_list.owner_id != user_id:
            raise PermissionDeniedError("You do not own this list.")
        return self.todo_repository.complete_item(item_id=item_id)


class ReopenTodoItemUseCase:

    def __init__(self, todo_repository):
        self.todo_repository = todo_repository

    def execute(self, user_id: str, list_id: str, item_id: str):
        todo_list = self.todo_repository.find_list_by_id(list_id)
        if todo_list is None:
            raise NotFoundError("Todo list not found.")
        if todo_list.owner_id != user_id:
            raise PermissionDeniedError("You do not own this list.")
        return self.todo_repository.reopen_item(item_id=item_id)


class RenameItemUseCase:

    def __init__(self, todo_repository):
        self.todo_repository = todo_repository

    def execute(self, user_id: str, list_id: str, item_id: str, new_content: str):
        todo_list = self.todo_repository.find_list_by_id(list_id)
        if todo_list is None:
            raise NotFoundError("Todo list not found.")
        if todo_list.owner_id != user_id:
            raise PermissionDeniedError("You do not own this list.")
        return self.todo_repository.rename_item(item_id=item_id, new_content=new_content)


class DeleteTodoListUseCase:

    def __init__(self, todo_repository):
        self.todo_repository = todo_repository

    def execute(self, user_id: str, list_id: str):
        todo_list = self.todo_repository.find_list_by_id(list_id)
        if todo_list is None:
            raise NotFoundError("Todo list not found.")
        if todo_list.owner_id != user_id:
            raise PermissionDeniedError("You do not own this list.")
        self.todo_repository.delete_list(list_id=list_id)