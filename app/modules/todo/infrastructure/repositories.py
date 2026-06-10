import uuid

from sqlalchemy.orm import Session

from modules.todo.domain.entities import TodoItem, TodoList, TaskStatus
from modules.todo.domain.ports import TodoItemRepositoryPort, TodoListRepositoryPort
from modules.todo.domain.value_objects import ListName
from modules.todo.infrastructure.orm_models import TodoItemORM, TodoListORM


class SQLAlchemyTodoListRepository(TodoListRepositoryPort):
    """implementacao do repositorio de listas de tarefas usando SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # converte um TodoItem de dominio para o modelo ORM
    def _item_to_orm(self, item: TodoItem, list_id: str) -> TodoItemORM:
        return TodoItemORM(
            id=str(item.id),
            todo_list_id=list_id,
            title=item.title,
            description=item.description,
            status=item.status.value,
            assigned_to=item.assigned_to,
            created_by=item.created_by,
            is_completed=item.completed,
            updated_at=item.updated_at,
        )

    # converte um modelo ORM para um TodoItem de dominio
    def _item_to_domain(self, orm: TodoItemORM) -> TodoItem:
        return TodoItem(
            id=uuid.UUID(orm.id),
            title=orm.title,
            created_by=orm.created_by,
            completed=orm.is_completed,
            description=orm.description,
            status=TaskStatus(orm.status),
            assigned_to=orm.assigned_to,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    # converte uma TodoList de dominio para o modelo ORM
    def _list_to_orm(self, todo_list: TodoList) -> TodoListORM:
        return TodoListORM(
            id=str(todo_list.id),
            owner_id=todo_list.owner_id,
            name=todo_list.name.value,
            created_at=todo_list.created_at,
        )

    # converte um modelo ORM para uma TodoList de dominio
    def _list_to_domain(self, orm: TodoListORM) -> TodoList:
        items = [self._item_to_domain(item) for item in orm.items]
        return TodoList(
            id=uuid.UUID(orm.id),
            name=ListName(orm.name),
            owner_id=orm.owner_id,
            items=items,
            created_at=orm.created_at,
        )

    # salva ou atualiza uma lista de tarefas no banco de dados
    def save(self, todo_list: TodoList) -> TodoList:
        list_id = str(todo_list.id)
        orm = self._list_to_orm(todo_list)

        # remove itens antigos e recria para manter consistencia do agregado
        self.session.query(TodoItemORM).filter_by(todo_list_id=list_id).delete()
        self.session.merge(orm)

        # adiciona os itens atuais
        item_orms = [self._item_to_orm(item, list_id) for item in todo_list.items]
        self.session.add_all(item_orms)
        self.session.commit()

        # recarrega do banco para retornar o estado persistido
        saved = self.session.get(TodoListORM, list_id)
        return self._list_to_domain(saved)

    # busca uma lista de tarefas pelo ID
    def find_by_id(self, todo_list_id: str) -> TodoList | None:
        orm = self.session.get(TodoListORM, todo_list_id)
        if orm is None:
            return None
        return self._list_to_domain(orm)

    # busca todas as listas de tarefas de um usuario
    def find_all_by_owner(self, owner_id: str) -> list[TodoList]:
        orms = (
            self.session.query(TodoListORM).filter_by(owner_id=owner_id).all()
        )
        return [self._list_to_domain(orm) for orm in orms]

    # remove uma lista de tarefas do banco de dados
    def delete(self, todo_list_id: str) -> None:
        self.session.query(TodoListORM).filter_by(id=todo_list_id).delete()
        self.session.commit()


class SQLAlchemyTodoItemRepository(TodoItemRepositoryPort):
    """implementacao do repositorio de itens/tarefas usando SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_orm(self, item: TodoItem) -> TodoItemORM:
        return TodoItemORM(
            id=str(item.id),
            title=item.title,
            description=item.description,
            status=item.status.value,
            assigned_to=item.assigned_to,
            created_by=item.created_by,
            is_completed=item.completed,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _to_domain(self, orm: TodoItemORM) -> TodoItem:
        return TodoItem(
            id=uuid.UUID(orm.id),
            title=orm.title,
            created_by=orm.created_by,
            completed=orm.is_completed,
            description=orm.description,
            status=TaskStatus(orm.status),
            assigned_to=orm.assigned_to,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def save(self, item: TodoItem) -> TodoItem:
        orm = self._to_orm(item)
        self.session.merge(orm)
        self.session.commit()
        saved = self.session.get(TodoItemORM, str(item.id))
        return self._to_domain(saved)

    def find_by_id(self, item_id: str) -> TodoItem | None:
        orm = self.session.get(TodoItemORM, item_id)
        if orm is None:
            return None
        return self._to_domain(orm)

    def find_by_assignee(self, user_id: str) -> list[TodoItem]:
        orms = (
            self.session.query(TodoItemORM)
            .filter_by(assigned_to=user_id, todo_list_id=None)
            .all()
        )
        return [self._to_domain(orm) for orm in orms]

    def delete(self, item_id: str) -> None:
        self.session.query(TodoItemORM).filter_by(id=item_id).delete()
        self.session.commit()
