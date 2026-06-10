# Módulo: Todo

> **Responsabilidade:** Gerenciamento completo de listas de tarefas e seus itens, com
> controle de propriedade (ownership) por usuário e operações de CRUD via aggregate root.

## Índice

- [Visão Geral](#visão-geral)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Domain](#domain)
- [Application](#application)
- [Infrastructure](#infrastructure)
- [Interface](#interface)
- [Repositórios](#repositórios)
- [Fluxos Principais](#fluxos-principais)
- [Dependências entre Módulos](#dependências-entre-módulos)

---

## Visão Geral

O módulo `todo` implementa o core da aplicação: o gerenciamento de listas de tarefas.
É o bounded context mais rico em termos de Domain-Driven Design, pois modela
explicitamente um **Aggregate** com `TodoList` como aggregate root e `TodoItem` como
entidade filha. Todas as mutações nos itens passam obrigatoriamente pela raiz do
agregado, que aplica regras de negócio (validação de estado, verificação de ownership).

O módulo segue estritamente a Arquitetura Hexagonal, com 7 use cases distintos e um
repositório que gerencia a persistência do agregado inteiro em uma única transação.

**Tecnologias específicas deste módulo:**
- Nenhuma além das bibliotecas padrão do projeto (SQLAlchemy para persistência)
- A lógica de autorização (verification de `owner_id`) é implementada como método de
  domínio na própria entidade `TodoList`

---

## Estrutura de Diretórios

```
app/modules/todo/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py                  ← TodoItem, TodoList (aggregate root)
│   ├── value_objects.py             ← ListName
│   ├── ports.py                     ← TodoListRepositoryPort (ABC)
│   └── exceptions.py                ← TodoListNotFoundError, AccessDeniedError, etc.
├── application/
│   ├── __init__.py
│   └── use_cases.py                 ← 7 use cases (Create, Get, AddItem, Complete, Reopen, Rename, Delete)
├── infrastructure/
│   ├── __init__.py
│   ├── orm_models.py                ← TodoListORM, TodoItemORM
│   └── repositories.py              ← SQLAlchemyTodoListRepository
├── adapters/
│   └── __init__.py                  ← (vazio — placeholder)
└── interface/
    ├── __init__.py
    ├── router.py                    ← 7 endpoints REST em /lists
    └── schemas.py                   ← Pydantic request/response schemas
```

---

## Domain

### Responsabilidade da Camada de Domain

A camada de domain do módulo `todo` encapsula todas as regras de negócio relacionadas a
listas de tarefas: o que significa completar um item, reabri-lo, renomeá-lo, e quem tem
permissão para modificar uma lista. O padrão **Aggregate** (do DDD) é aplicado com
`TodoList` como raiz — toda modificação em `TodoItem` é mediada por `TodoList`.

### Entidades

#### `TodoItem`

**Arquivo:** `app/modules/todo/domain/entities.py`

**Descrição:** Representa um item individual dentro de uma lista de tarefas. Não possui
existência independente fora do agregado `TodoList`. Contém regras de transição de estado
(completar/reabrir).

**Propriedades:**

| Propriedade  | Tipo         | Descrição                                       |
|--------------|--------------|-------------------------------------------------|
| `id`         | `uuid.UUID`  | Identificador único (UUID4)                     |
| `title`      | `str`        | Título descritivo do item                       |
| `completed`  | `bool`       | Estado de conclusão (default `False`)           |
| `created_at` | `datetime`   | Data/hora de criação (UTC)                      |

**Regras de Negócio / Invariantes:**
- Um item já concluído não pode ser concluído novamente (`AlreadyCompletedError`)
- Um item não concluído não pode ser reaberto (`NotCompletedError`)
- Um item não pode ter título vazio (`EmptyTitleError`)

```python
@dataclass(kw_only=True)
class TodoItem:
    title: str
    completed: bool = False
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def complete(self):
        if self.completed:
            raise AlreadyCompletedError()
        self.completed = True

    def reopen(self):
        if not self.completed:
            raise NotCompletedError()
        self.completed = False

    def rename(self, new_title: str):
        if not new_title.strip():
            raise EmptyTitleError()
        self.title = new_title
```

#### `TodoList` (Aggregate Root)

**Arquivo:** `app/modules/todo/domain/entities.py`

**Descrição:** Raiz do agregado de lista de tarefas. Contém uma coleção de `TodoItem` e
é o único ponto de entrada para qualquer modificação nos itens. Aplica verificações de
propriedade (ownership) e delega operações aos itens.

**Propriedades:**

| Propriedade  | Tipo              | Descrição                                    |
|--------------|-------------------|----------------------------------------------|
| `id`         | `uuid.UUID`       | Identificador único (UUID4)                  |
| `name`       | `ListName`        | Nome da lista (value object com validação)   |
| `owner_id`   | `str`             | UUID do usuário dono da lista                |
| `items`      | `list[TodoItem]`  | Coleção de itens da lista                    |
| `created_at` | `datetime`        | Data/hora de criação (UTC)                   |

**Regras de Negócio / Invariantes:**
- Apenas o `owner_id` (dono) pode modificar a lista (`verify_ownership`)
- Todo item adicionado deve ter título não vazio (`add_item` valida)
- Itens são acessados por ID via método privado `_get_item` (único ponto de lookup)
- Método `remove_item` permite exclusão lógica de itens do agregado

**Código completo:**

```python
@dataclass(kw_only=True)
class TodoList:
    name: ListName
    owner_id: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    items: list[TodoItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def _get_item(self, item_id: uuid.UUID) -> TodoItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise TodoItemNotFoundError(str(item_id))

    def add_item(self, title: str) -> TodoItem:
        if not title.strip():
            raise EmptyTitleError()
        item = TodoItem(title=title)
        self.items.append(item)
        return item

    def complete_item(self, item_id: uuid.UUID):
        item = self._get_item(item_id)
        item.complete()

    def reopen_item(self, item_id: uuid.UUID):
        item = self._get_item(item_id)
        item.reopen()

    def rename_item(self, item_id: uuid.UUID, new_title: str):
        item = self._get_item(item_id)
        item.rename(new_title)

    def remove_item(self, item_id: uuid.UUID):
        item = self._get_item(item_id)
        self.items.remove(item)

    def verify_ownership(self, user_id: str):
        if self.owner_id != user_id:
            raise AccessDeniedError()
```

### Value Objects

#### `ListName`

**Arquivo:** `app/modules/todo/domain/value_objects.py`

**Descrição:** Value object imutável para o nome de uma lista de tarefas. Garante que o
nome não seja vazio e não exceda 100 caracteres.

```python
@dataclass(frozen=True)
class ListName:
    value: str

    def __post_init__(self):
        if not self.value.strip():
            raise ValueError("List name cannot be blank")
        if len(self.value) > 100:
            raise ValueError("List name cannot exceed 100 characters")
```

### Domain Exceptions

**Arquivo:** `app/modules/todo/domain/exceptions.py`

```python
class TodoListNotFoundError(Exception):
    def __init__(self, list_id: str):
        self.list_id = list_id
        super().__init__(f"TodoList with id {list_id} not found")

class TodoItemNotFoundError(Exception):
    def __init__(self, item_id: str):
        self.item_id = item_id
        super().__init__(f"TodoItem with id {item_id} not found")

class AlreadyCompletedError(Exception):
    """Item já está concluído — não pode ser concluído novamente."""
    pass

class NotCompletedError(Exception):
    """Item não está concluído — não pode ser reaberto."""
    pass

class EmptyTitleError(Exception):
    """Título do item não pode ser vazio."""
    pass

class AccessDeniedError(Exception):
    """Usuário não é o dono da lista."""
    pass
```

### Domain Events

> ⚠️ **Não implementado.** O projeto não possui eventos de domínio. Nenhuma entidade
> dispara eventos (como `TodoItemCompleted`, `TodoListCreated`). Esta seria uma extensão
> natural para cenários como notificações ou auditoria.

---

## Application

### Responsabilidade da Camada de Application

Contém 7 use cases que orquestram as operações sobre listas de tarefas. Cada use case
segue o mesmo padrão:
1. Carregar o agregado via repositório (ou criar novo)
2. Verificar ownership (`verify_ownership`)
3. Delegar para método de domínio no agregado
4. Persistir via repositório
5. Retornar o agregado atualizado

### Use Cases

#### `CreateTodoListUseCase`

**Arquivo:** `app/modules/todo/application/use_cases.py`

**Descrição:** Cria uma nova lista de tarefas para um usuário.

**Input:** `name: str`, `owner_id: str`
**Output:** `TodoList`

```python
class CreateTodoListUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, name: str, owner_id: str) -> TodoList:
        todo_list = TodoList(name=ListName(name), owner_id=owner_id)
        return self._repo.save(todo_list)
```

#### `GetUserTodoListsUseCase`

**Descrição:** Retorna todas as listas de tarefas pertencentes a um usuário.

**Input:** `owner_id: str`
**Output:** `list[TodoList]`

```python
class GetUserTodoListsUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, owner_id: str) -> list[TodoList]:
        return self._repo.find_all_by_owner(owner_id)
```

#### `AddTodoItemUseCase`

**Descrição:** Adiciona um novo item a uma lista existente.

**Input:** `list_id: str`, `title: str`, `user_id: str`
**Output:** `TodoList`

**Fluxo interno:**
1. Busca lista por ID — se não encontrada, `TodoListNotFoundError`
2. Verifica se `user_id` é o dono da lista — se não, `AccessDeniedError`
3. Adiciona item via `todo_list.add_item(title)` — valida título não vazio
4. Persiste o agregado atualizado
5. Retorna o agregado

```python
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
```

#### `CompleteTodoItemUseCase`

**Descrição:** Marca um item como concluído. Dispara `AlreadyCompletedError` se o item
já estiver concluído.

**Input:** `list_id: str`, `item_id: uuid.UUID`, `user_id: str`
**Output:** `TodoList`

```python
class CompleteTodoItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, item_id: uuid.UUID, user_id: str) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        todo_list.complete_item(item_id)
        return self._repo.save(todo_list)
```

#### `ReopenTodoItemUseCase`

**Descrição:** Reabre um item que estava concluído. Dispara `NotCompletedError` se o
item não estiver concluído.

**Input:** `list_id: str`, `item_id: uuid.UUID`, `user_id: str`
**Output:** `TodoList`

```python
class ReopenTodoItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, item_id: uuid.UUID, user_id: str) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        todo_list.reopen_item(item_id)
        return self._repo.save(todo_list)
```

#### `RenameItemUseCase`

**Descrição:** Renomeia o título de um item. Valida que o novo título não é vazio.

**Input:** `list_id: str`, `item_id: uuid.UUID`, `new_title: str`, `user_id: str`
**Output:** `TodoList`

```python
class RenameItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, item_id: uuid.UUID, new_title: str, user_id: str) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        todo_list.rename_item(item_id, new_title)
        return self._repo.save(todo_list)
```

#### `DeleteTodoListUseCase`

**Descrição:** Remove uma lista de tarefas por completo (incluindo todos os seus itens,
via cascade no ORM).

**Input:** `list_id: str`, `user_id: str`
**Output:** `None`

```python
class DeleteTodoListUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, user_id: str) -> None:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)
        self._repo.delete(list_id)
```

> 💡 **Nota sobre o método `_get_list_or_raise`**: Este método privado aparece duplicado
> em 5 dos 7 use cases. Representa uma oportunidade de refatoração (extrair para classe
> base ou helper).

### Ports (Interfaces de Application)

O módulo define um único port de infraestrutura:

`TodoListRepositoryPort` (`app/modules/todo/domain/ports.py`):

```python
class TodoListRepositoryPort(ABC):
    @abstractmethod
    def save(self, todo_list: TodoList) -> TodoList: ...
    @abstractmethod
    def find_by_id(self, todo_list_id: str) -> TodoList | None: ...
    @abstractmethod
    def find_all_by_owner(self, owner_id: str) -> list[TodoList]: ...
    @abstractmethod
    def delete(self, todo_list_id: str) -> None: ...
```

Não há ports para `TodoItem` isoladamente — os itens são persistidos como parte do
agregado `TodoList`.

---

## Infrastructure

### Responsabilidade da Camada de Infrastructure

Contém os modelos ORM e a implementação concreta do repositório. Como o módulo `todo`
não depende de serviços externos além do banco de dados, a infrastructure é mais enxuta
que a do módulo `auth`.

### ORM Entities

#### `TodoListORM`

**Arquivo:** `app/modules/todo/infrastructure/orm_models.py`
**Tabela mapeada:** `todo_lists`

```python
class TodoListORM(Base):
    __tablename__ = "todo_lists"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    items: Mapped[list["TodoItemORM"]] = relationship(
        "TodoItemORM", back_populates="todo_list", cascade="all, delete-orphan"
    )
```

**Relacionamento**: `TodoListORM.items → TodoItemORM.todo_list` (bidirecional, um-para-muitos).
`cascade="all, delete-orphan"` garante que deletar uma lista remove todos os seus itens.

#### `TodoItemORM`

**Arquivo:** `app/modules/todo/infrastructure/orm_models.py`
**Tabela mapeada:** `todo_items`

```python
class TodoItemORM(Base):
    __tablename__ = "todo_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    todo_list_id: Mapped[str] = mapped_column(String, ForeignKey("todo_lists.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    todo_list: Mapped["TodoListORM"] = relationship("TodoListORM", back_populates="items")
```

**Nota sobre nomenclatura:** O campo `is_completed` no ORM corresponde ao atributo
`completed` na entidade de domínio `TodoItem`. O mapeamento é feito explicitamente no
repositório.

### Repositório (Implementação Concreta)

#### `SQLAlchemyTodoListRepository` → implementa `TodoListRepositoryPort`

**Arquivo:** `app/modules/todo/infrastructure/repositories.py`

```python
class SQLAlchemyTodoListRepository(TodoListRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Mapeamento TodoItem ──

    def _item_to_orm(self, item: TodoItem, list_id: str) -> TodoItemORM:
        return TodoItemORM(
            id=str(item.id),
            todo_list_id=list_id,
            title=item.title,
            is_completed=item.completed,
        )

    def _item_to_domain(self, orm: TodoItemORM) -> TodoItem:
        return TodoItem(
            id=uuid.UUID(orm.id),
            title=orm.title,
            completed=orm.is_completed,
            created_at=orm.created_at,
        )

    # ── Mapeamento TodoList ──

    def _list_to_orm(self, todo_list: TodoList) -> TodoListORM:
        return TodoListORM(
            id=str(todo_list.id),
            owner_id=todo_list.owner_id,
            name=todo_list.name.value,
            created_at=todo_list.created_at,
        )

    def _list_to_domain(self, orm: TodoListORM) -> TodoList:
        items = [self._item_to_domain(item) for item in orm.items]
        return TodoList(
            id=uuid.UUID(orm.id),
            name=ListName(orm.name),
            owner_id=orm.owner_id,
            items=items,
            created_at=orm.created_at,
        )

    # ── Operações do repositório ──

    def save(self, todo_list: TodoList) -> TodoList:
        list_id = str(todo_list.id)
        orm = self._list_to_orm(todo_list)

        # Delete + reinsert para consistência do agregado
        self.session.query(TodoItemORM).filter_by(todo_list_id=list_id).delete()
        self.session.merge(orm)

        item_orms = [self._item_to_orm(item, list_id) for item in todo_list.items]
        self.session.add_all(item_orms)
        self.session.commit()

        saved = self.session.get(TodoListORM, list_id)
        return self._list_to_domain(saved)

    def find_by_id(self, todo_list_id: str) -> TodoList | None:
        orm = self.session.get(TodoListORM, todo_list_id)
        if orm is None:
            return None
        return self._list_to_domain(orm)

    def find_all_by_owner(self, owner_id: str) -> list[TodoList]:
        orms = self.session.query(TodoListORM).filter_by(owner_id=owner_id).all()
        return [self._list_to_domain(orm) for orm in orms]

    def delete(self, todo_list_id: str) -> None:
        self.session.query(TodoListORM).filter_by(id=todo_list_id).delete()
        self.session.commit()
```

**Estratégia de persistência do agregado**: O método `save` usa a estratégia
**delete-all + reinsert** para manter os itens do agregado consistentes:
1. Remove todos os `todo_items` existentes para aquela lista
2. Faz `merge` da `todo_list` (upsert)
3. Insere todos os itens atuais do agregado
4. Commita a transação
5. Recarrega do banco para retornar o estado persistido com dados gerados (timestamps,
   defaults)

Esta abordagem é simples e garante que não haja itens órfãos, mas em cenários com
muitos itens por lista ou alta concorrência, uma estratégia de diff (detectar itens
adicionados/removidos/modificados) seria mais eficiente.

---

## Interface

### Responsabilidade da Camada de Interface

Expõe 7 endpoints REST para o gerenciamento de listas e itens. Todos os endpoints
(exceto documentação implícita) requerem autenticação JWT via
`Depends(get_current_user_id)`. Nenhum endpoint contém lógica de negócio — apenas
orquestração de dependências, execução de use cases e mapeamento de exceções para HTTP.

### Rotas expostas

| Método | Path                                         | Use Case                     | Auth         |
|--------|----------------------------------------------|------------------------------|--------------|
| GET    | `/lists/`                                    | `GetUserTodoListsUseCase`    | Bearer JWT   |
| POST   | `/lists/`                                    | `CreateTodoListUseCase`      | Bearer JWT   |
| DELETE | `/lists/{list_id}`                           | `DeleteTodoListUseCase`      | Bearer JWT   |
| POST   | `/lists/{list_id}/items`                     | `AddTodoItemUseCase`         | Bearer JWT   |
| PATCH  | `/lists/{list_id}/items/{item_id}/complete`  | `CompleteTodoItemUseCase`    | Bearer JWT   |
| PATCH  | `/lists/{list_id}/items/{item_id}/reopen`    | `ReopenTodoItemUseCase`      | Bearer JWT   |
| PATCH  | `/lists/{list_id}/items/{item_id}/rename`    | `RenameItemUseCase`          | Bearer JWT   |

### Schemas (DTOs de Interface)

**Arquivo:** `app/modules/todo/interface/schemas.py`

```python
class CreateListRequest(BaseModel):
    name: str

class AddItemRequest(BaseModel):
    title: str

class RenameItemRequest(BaseModel):
    title: str

class TodoItemResponse(BaseModel):
    id: UUID
    title: str
    is_completed: bool
    created_at: datetime

class TodoListResponse(BaseModel):
    id: UUID
    name: str
    owner_id: str
    created_at: datetime
    items: list[TodoItemResponse]
```

### Controllers

Todos os controllers seguem o mesmo padrão. Exemplo representativo — criar lista e
adicionar item:

**`POST /lists/`** (`app/modules/todo/interface/router.py:62`):

```python
@router.post("/", response_model=TodoListResponse, status_code=201)
def create_list(body: CreateListRequest, user_id: UUID = Depends(get_current_user_id),
                db: Session = Depends(get_db)):
    repo = SQLAlchemyTodoListRepository(db)
    uc = CreateTodoListUseCase(repo=repo)
    todo_list = uc.execute(name=body.name, owner_id=str(user_id))
    return TodoListResponse(
        id=todo_list.id, name=todo_list.name.value,
        owner_id=todo_list.owner_id, created_at=todo_list.created_at, items=[]
    )
```

**`POST /lists/{list_id}/items`** (`app/modules/todo/interface/router.py:96`):

```python
@router.post("/{list_id}/items", response_model=TodoListResponse, status_code=201)
def add_item(list_id: UUID, body: AddItemRequest,
             user_id: UUID = Depends(get_current_user_id), db: Session = Depends(get_db)):
    repo = SQLAlchemyTodoListRepository(db)
    uc = AddTodoItemUseCase(repo=repo)
    try:
        todo_list = uc.execute(list_id=str(list_id), title=body.title, user_id=str(user_id))
    except AccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except TodoListNotFoundError:
        raise HTTPException(status_code=404, detail="List not found")
    return TodoListResponse(
        id=todo_list.id, name=todo_list.name.value,
        owner_id=todo_list.owner_id, created_at=todo_list.created_at,
        items=[TodoItemResponse(id=item.id, title=item.title,
                is_completed=item.completed, created_at=item.created_at)
               for item in todo_list.items],
    )
```

### Mapeamento de exceções

| Exceção de domínio          | Código HTTP | Mensagem         |
|-----------------------------|-------------|------------------|
| `TodoListNotFoundError`     | 404         | "List not found" |
| `AccessDeniedError`         | 403         | "Access denied"  |

> ⚠️ **Exceções não tratadas**: `AlreadyCompletedError`, `NotCompletedError` e
> `EmptyTitleError` não são capturadas nos controllers. Resultariam em HTTP 500 se
> disparadas. Também não há um middleware global para capturá-las.

---

## Repositórios

### Padrão Repository neste Módulo

O módulo define um único repositório para o agregado `TodoList`. `TodoItem` não possui
repositório próprio — é sempre acessado e modificado através do `TodoList` (aggregate
root).

### Diagrama de Dependência

```
CreateTodoListUseCase / AddTodoItemUseCase / ... / DeleteTodoListUseCase
  │  depende de (via construtor)
  ▼
TodoListRepositoryPort              ← interface no domain (port)
  ▲
  │  implementado por
SQLAlchemyTodoListRepository        ← classe na infrastructure (adapter)
  │  usa internamente
  ▼
SQLAlchemy Session + TodoListORM / TodoItemORM
  │  conecta a
  ▼
SQLite / PostgreSQL
```

### Métodos do Repositório

```python
class TodoListRepositoryPort(ABC):
    def save(self, todo_list: TodoList) -> TodoList:
        """Persiste o agregado completo (lista + itens).
        Usa estratégia delete-and-reinsert para itens."""

    def find_by_id(self, todo_list_id: str) -> TodoList | None:
        """Busca uma lista pelo ID e reconstrói o agregado completo (com itens)."""

    def find_all_by_owner(self, owner_id: str) -> list[TodoList]:
        """Busca todas as listas pertencentes a um usuário, com seus itens."""

    def delete(self, todo_list_id: str) -> None:
        """Remove a lista e todos os seus itens (cascade no ORM)."""
```

---

## Fluxos Principais

### Fluxo 1: Criar Lista de Tarefas

**Descrição:** Usuário autenticado cria uma nova lista de tarefas com um nome.

**Sequência:**

```
Cliente HTTP
  │
  │  POST /lists/ { "name": "Compras" }
  │  Authorization: Bearer eyJ...
  ▼
todo/interface/router.py::create_list()
  │  FastAPI extrai user_id do JWT via get_current_user_id()
  │  FastAPI valida body contra CreateListRequest
  │  Controller instancia:
  │    repo = SQLAlchemyTodoListRepository(db)
  │    uc = CreateTodoListUseCase(repo)
  ▼
todo/application/use_cases.py::CreateTodoListUseCase.execute()
  │  1. Cria ListName("Compras") → valida não vazio e ≤ 100 chars
  │  2. Cria TodoList(name=ListName("Compras"), owner_id=str(user_id))
  │     → id = uuid4(), items = [], created_at = now()
  │  3. repo.save(todo_list)
  │     → _list_to_orm() converte domain → TodoListORM
  │     → session.merge(orm) insere na tabela todo_lists
  │     → session.commit()
  │     → session.get() recarrega do banco
  │     → _list_to_domain() reconverte para retornar
  ▼
HTTP 201 { "id": "uuid", "name": "Compras", "owner_id": "user-uuid",
           "created_at": "...", "items": [] }
```

**Regras de negócio aplicadas:**
- Nome da lista não pode ser vazio (validado por `ListName.__post_init__`)
- Nome da lista não pode exceder 100 caracteres (validado por `ListName.__post_init__`)
- `owner_id` é extraído do token JWT — o usuário sempre cria listas para si mesmo

**Erros possíveis:**
- `ValueError` do `ListName` → ⚠️ resultaria em HTTP 500 (não tratado)

### Fluxo 2: Adicionar Item a uma Lista

**Descrição:** Usuário dono de uma lista adiciona um novo item a ela.

**Sequência:**

```
Cliente HTTP
  │
  │  POST /lists/{list_id}/items { "title": "Comprar pão" }
  ▼
todo/interface/router.py::add_item()
  │  Controller instancia repo, AddTodoItemUseCase
  ▼
todo/application/use_cases.py::AddTodoItemUseCase.execute()
  │  1. todo_list = repo.find_by_id(list_id)
  │     → SQL: SELECT * FROM todo_lists WHERE id = ?
  │     → Carrega items via relacionamento (lazy load ou JOIN)
  │  2. Se None → TodoListNotFoundError
  │  3. todo_list.verify_ownership(user_id)
  │     → compara owner_id com user_id do JWT
  │     → se diferente → AccessDeniedError
  │  4. todo_list.add_item("Comprar pão")
  │     → valida título não vazio
  │     → cria TodoItem(title="Comprar pão", completed=False)
  │     → append ao items do agregado
  │  5. repo.save(todo_list)
  │     → DELETE todos os items antigos da lista
  │     → MERGE a lista
  │     → INSERT todos os items atuais
  │     → COMMIT
  ▼
HTTP 201 { "id": "list-uuid", "name": "Compras", ..., "items": [
    { "id": "item-uuid", "title": "Comprar pão", "is_completed": false, ... }
]}
```

**Regras de negócio aplicadas:**
- Apenas o dono (`owner_id`) pode modificar a lista
- Título do item não pode ser vazio
- A lista deve existir (404 se não encontrada)

### Fluxo 3: Completar um Item

**Descrição:** Usuário marca um item como concluído.

**Sequência:**

```
Cliente HTTP
  │
  │  PATCH /lists/{list_id}/items/{item_id}/complete
  ▼
todo/application/use_cases.py::CompleteTodoItemUseCase.execute()
  │  1. Carrega lista, verifica ownership
  │  2. todo_list.complete_item(item_id)
  │     → _get_item(item_id) busca item na coleção
  │     → item.complete()
  │        → se completed=True → AlreadyCompletedError
  │        → seta completed=True
  │  3. repo.save(todo_list)
  ▼
HTTP 200 { ... lista atualizada ... }
```

**Regras de negócio aplicadas:**
- Item já concluído não pode ser concluído novamente (idempotência com erro)
- Apenas o dono pode completar itens
- O item deve existir na lista

---

## Dependências entre Módulos

### Este módulo depende de:

| Módulo  | O que usa                           | Justificativa                              |
|---------|-------------------------------------|--------------------------------------------|
| shared  | `Base`                              | Classe base SQLAlchemy para ORM models     |
| shared  | `get_db()`                          | Injeção de sessão nos controllers          |
| shared  | `get_current_user_id()`             | Extração do user_id do JWT nos controllers |
| auth    | Indiretamente via `get_current_user_id` | O módulo auth gera o token JWT que o todo verifica |

### Outros módulos que dependem deste:

Nenhum. O módulo `todo` é autossuficiente e não exporta interfaces consumidas por outros
módulos de feature.

### Regra de Dependência

O módulo `todo` depende apenas de `shared` para concerns transversais. A dependência
sobre `auth` é indireta (via `shared/dependencies.py`). O módulo `todo` não importa
diretamente nenhuma classe do módulo `auth`, respeitando a fronteira entre bounded
contexts.

---

[← Voltar ao Index](../index.md)
