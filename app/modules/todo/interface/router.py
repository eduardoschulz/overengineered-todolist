from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from modules.todo.application.use_cases import (
    AddTodoItemUseCase,
    CompleteTodoItemUseCase,
    CreateTodoListUseCase,
    DeleteTodoListUseCase,
    GetUserTodoListsUseCase,
    RenameItemUseCase,
    ReopenTodoItemUseCase,
)
from modules.todo.domain.exceptions import (
    AccessDeniedError,
    TodoListNotFoundError,
)
from modules.todo.infrastructure.repositories import SQLAlchemyTodoListRepository
from modules.todo.interface.schemas import (
    AddItemRequest,
    CreateListRequest,
    RenameItemRequest,
    TodoItemResponse,
    TodoListResponse,
)
from shared.database import get_db
from shared.dependencies import get_current_user_id

router = APIRouter(prefix="/lists", tags=["todo"])


@router.get("/", response_model=list[TodoListResponse])
def list_lists(
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """retorna todas as listas do usuario autenticado."""
    repo = SQLAlchemyTodoListRepository(db)
    uc = GetUserTodoListsUseCase(repo=repo)
    todo_lists = uc.execute(owner_id=str(user_id))
    return [
        TodoListResponse(
            id=tl.id,
            name=tl.name.value,
            owner_id=tl.owner_id,
            created_at=tl.created_at,
            items=[
                TodoItemResponse(
                    id=item.id,
                    title=item.title,
                    is_completed=item.completed,
                    created_at=item.created_at,
                )
                for item in tl.items
            ],
        )
        for tl in todo_lists
    ]


@router.post("/", response_model=TodoListResponse, status_code=201)
def create_list(
    body: CreateListRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """cria uma nova lista de tarefas."""
    repo = SQLAlchemyTodoListRepository(db)
    uc = CreateTodoListUseCase(repo=repo)
    todo_list = uc.execute(name=body.name, owner_id=str(user_id))
    return TodoListResponse(
        id=todo_list.id,
        name=todo_list.name.value,
        owner_id=todo_list.owner_id,
        created_at=todo_list.created_at,
        items=[],
    )


@router.delete("/{list_id}", status_code=204)
def delete_list(
    list_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """remove uma lista de tarefas."""
    repo = SQLAlchemyTodoListRepository(db)
    uc = DeleteTodoListUseCase(repo=repo)
    try:
        uc.execute(list_id=str(list_id), user_id=str(user_id))
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("/{list_id}/items", response_model=TodoListResponse, status_code=201)
def add_item(
    list_id: UUID,
    body: AddItemRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """adiciona um item a uma lista de tarefas."""
    repo = SQLAlchemyTodoListRepository(db)
    uc = AddTodoItemUseCase(repo=repo)
    try:
        todo_list = uc.execute(
            list_id=str(list_id), title=body.title, user_id=str(user_id)
        )
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except TodoListNotFoundError:
        raise HTTPException(status_code=404, detail="List not found")
    return TodoListResponse(
        id=todo_list.id,
        name=todo_list.name.value,
        owner_id=todo_list.owner_id,
        created_at=todo_list.created_at,
        items=[
            TodoItemResponse(
                id=item.id,
                title=item.title,
                is_completed=item.completed,
                created_at=item.created_at,
            )
            for item in todo_list.items
        ],
    )


@router.patch(
    "/{list_id}/items/{item_id}/complete", response_model=TodoListResponse
)
def complete_item(
    list_id: UUID,
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """marca um item como concluido."""
    repo = SQLAlchemyTodoListRepository(db)
    uc = CompleteTodoItemUseCase(repo=repo)
    try:
        todo_list = uc.execute(
            list_id=str(list_id), item_id=item_id, user_id=str(user_id)
        )
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except TodoListNotFoundError:
        raise HTTPException(status_code=404, detail="List not found")
    return TodoListResponse(
        id=todo_list.id,
        name=todo_list.name.value,
        owner_id=todo_list.owner_id,
        created_at=todo_list.created_at,
        items=[
            TodoItemResponse(
                id=item.id,
                title=item.title,
                is_completed=item.completed,
                created_at=item.created_at,
            )
            for item in todo_list.items
        ],
    )


@router.patch(
    "/{list_id}/items/{item_id}/reopen", response_model=TodoListResponse
)
def reopen_item(
    list_id: UUID,
    item_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """reabre um item que estava concluido."""
    repo = SQLAlchemyTodoListRepository(db)
    uc = ReopenTodoItemUseCase(repo=repo)
    try:
        todo_list = uc.execute(
            list_id=str(list_id), item_id=item_id, user_id=str(user_id)
        )
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except TodoListNotFoundError:
        raise HTTPException(status_code=404, detail="List not found")
    return TodoListResponse(
        id=todo_list.id,
        name=todo_list.name.value,
        owner_id=todo_list.owner_id,
        created_at=todo_list.created_at,
        items=[
            TodoItemResponse(
                id=item.id,
                title=item.title,
                is_completed=item.completed,
                created_at=item.created_at,
            )
            for item in todo_list.items
        ],
    )


@router.patch(
    "/{list_id}/items/{item_id}/rename", response_model=TodoListResponse
)
def rename_item(
    list_id: UUID,
    item_id: UUID,
    body: RenameItemRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """renomeia o titulo de um item."""
    repo = SQLAlchemyTodoListRepository(db)
    uc = RenameItemUseCase(repo=repo)
    try:
        todo_list = uc.execute(
            list_id=str(list_id),
            item_id=item_id,
            new_title=body.title,
            user_id=str(user_id),
        )
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except TodoListNotFoundError:
        raise HTTPException(status_code=404, detail="List not found")
    return TodoListResponse(
        id=todo_list.id,
        name=todo_list.name.value,
        owner_id=todo_list.owner_id,
        created_at=todo_list.created_at,
        items=[
            TodoItemResponse(
                id=item.id,
                title=item.title,
                is_completed=item.completed,
                created_at=item.created_at,
            )
            for item in todo_list.items
        ],
    )
