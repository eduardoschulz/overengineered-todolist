import uuid

from sqlalchemy.orm import Session

from modules.todo.domain.entities import TodoItem, TodoList
from modules.todo.domain.ports import TodoListRepositoryPort
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
            is_completed=item.completed,
        )

    # converte um modelo ORM para um TodoItem de dominio
    def _item_to_domain(self, orm: TodoItemORM) -> TodoItem:
        return TodoItem(
            id=uuid.UUID(orm.id),
            title=orm.title,
            completed=orm.is_completed,
            created_at=orm.created_at,
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
