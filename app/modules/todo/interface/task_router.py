from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from modules.todo.application.use_cases import (
    CreateTaskUseCase,
    DeleteTaskUseCase,
    GetTaskUseCase,
    ListTasksByAssigneeUseCase,
    UpdateTaskUseCase,
)
from modules.todo.domain.entities import TaskStatus
from modules.todo.domain.exceptions import (
    AccessDeniedError,
    EmptyTitleError,
    TodoItemNotFoundError,
)
from modules.todo.infrastructure.repositories import SQLAlchemyTodoItemRepository
from modules.todo.interface.schemas import (
    CreateTaskRequest,
    TaskResponse,
    UpdateTaskRequest,
)
from shared.database import get_db
from shared.dependencies import get_current_user_id

tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])


@tasks_router.post("/", response_model=TaskResponse, status_code=201)
def create_task(
    body: CreateTaskRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """cria uma nova tarefa."""
    repo = SQLAlchemyTodoItemRepository(db)
    uc = CreateTaskUseCase(repo=repo)
    try:
        task = uc.execute(
            title=body.title,
            created_by=str(user_id),
            description=body.description,
            status=TaskStatus(body.status),
            assigned_to=body.assigned_to,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status value")
    except EmptyTitleError:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        assigned_to=task.assigned_to,
        created_by=task.created_by,
        is_completed=task.completed,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@tasks_router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """retorna uma tarefa por id."""
    repo = SQLAlchemyTodoItemRepository(db)
    uc = GetTaskUseCase(repo=repo)
    try:
        task = uc.execute(task_id=str(task_id))
    except TodoItemNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        assigned_to=task.assigned_to,
        created_by=task.created_by,
        is_completed=task.completed,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@tasks_router.get("/", response_model=list[TaskResponse])
def list_tasks(
    assignedTo: str | None = Query(None),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """lista tarefas atribuidas a um usuario especifico."""
    if not assignedTo:
        return []
    repo = SQLAlchemyTodoItemRepository(db)
    uc = ListTasksByAssigneeUseCase(repo=repo)
    tasks = uc.execute(user_id=assignedTo)
    return [
        TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status.value,
            assigned_to=task.assigned_to,
            created_by=task.created_by,
            is_completed=task.completed,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]


@tasks_router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    body: UpdateTaskRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """atualiza titulo, descricao e/ou status da tarefa."""
    repo = SQLAlchemyTodoItemRepository(db)
    uc = UpdateTaskUseCase(repo=repo)
    status = TaskStatus(body.status) if body.status else None
    try:
        task = uc.execute(
            task_id=str(task_id),
            user_id=str(user_id),
            title=body.title,
            description=body.description,
            status=status,
            assigned_to=body.assigned_to,
        )
    except TodoItemNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except (ValueError, EmptyTitleError):
        raise HTTPException(status_code=400, detail="Invalid request body")
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        assigned_to=task.assigned_to,
        created_by=task.created_by,
        is_completed=task.completed,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@tasks_router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """remove uma tarefa."""
    repo = SQLAlchemyTodoItemRepository(db)
    uc = DeleteTaskUseCase(repo=repo)
    try:
        uc.execute(task_id=str(task_id), user_id=str(user_id))
    except TodoItemNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
