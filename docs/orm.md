# Persistência e ORM

## Índice

- [ORM Utilizado](#orm-utilizado)
- [Configuração da Conexão](#configuração-da-conexão)
- [Estratégia de Mapeamento](#estratégia-de-mapeamento-entidades-orm-vs-entidades-de-domínio)
- [Entities / Models Existentes](#entities--models-existentes)
- [Migrations](#migrations)
- [Repositories — Padrão Aplicado](#repositories--padrão-aplicado)
- [Transações](#transações)
- [Queries Complexas](#queries-complexas)

---

## ORM Utilizado

| Atributo            | Valor                            |
|---------------------|----------------------------------|
| **ORM**             | SQLAlchemy 2.x                   |
| **Estilo**          | DeclarativeBase + `Mapped`/`mapped_column` (moderno) |
| **Banco alvo (dev)** | SQLite                           |
| **Banco alvo (prod)**| PostgreSQL 16 (via Docker Compose)|

**Motivação**: SQLAlchemy foi escolhido por ser o ORM mais maduro e flexível do
ecossistema Python, com suporte ao padrão Data Mapper (separação entre modelo de
persistência e modelo de domínio) e ao novo estilo declarativo com type hints.

---

## Configuração da Conexão

### Arquivo de configuração

A configuração é centralizada em `app/shared/config.py`, usando Pydantic-Settings para
ler de um arquivo `.env`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE)
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_TTL_MINUTES: int = 30

settings = Settings()
```

### Exemplo de `.env` (dev — SQLite)

```
DATABASE_URL=sqlite:///./todo_app.db
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_TTL_MINUTES=30
```

### Criação do Engine e Session

Em `app/shared/database.py`, o engine e a session factory são criados como singletons
de módulo:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.config import settings

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(engine)

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
```

`get_db()` é um **generator** usado como dependência FastAPI. Cada requisição recebe
uma sessão nova, que é fechada no `finally` ao fim da requisição.

### Variação por ambiente

| Ambiente | DATABASE_URL                                         |
|----------|------------------------------------------------------|
| Dev      | `sqlite:///./todo_app.db`                             |
| Test     | `sqlite:///./test.db` (definido em `conftest.py`)     |
| Prod     | `postgresql://user:password@localhost:5432/todolist`  |

Para testes, o `conftest.py` cria um engine separado com `check_same_thread=False`
(necessário para SQLite com FastAPI):

```python
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(test_engine)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

# Sobrescreve a dependência get_db nos testes
app.dependency_overrides[get_db] = override_get_db
```

---

## Estratégia de Mapeamento (Entidades ORM vs Entidades de Domínio)

### Data Mapper Puro

O projeto adota **separação total** entre modelo de persistência e modelo de domínio
(padrão **Data Mapper**). As entidades ORM (`*ORM`) residem em
`infrastructure/orm_models.py` e são completamente independentes das entidades de domínio
(`User`, `TodoList`, `TodoItem`) que residem em `domain/entities.py`.

Este é um dos aspectos mais "overengineered" do projeto, mas demonstra o princípio
arquitetural corretamente.

### Prós e Contras no contexto do projeto

| Prós                                                              | Contras                                                          |
|-------------------------------------------------------------------|------------------------------------------------------------------|
| Domínio 100% isolado de detalhes de ORM                           | Código adicional de mapeamento (`_to_orm`, `_to_domain`)         |
| Trocar ORM não afeta o domínio                                    | Duplicação conceitual (User e UserORM têm campos similares)      |
| Entidades de domínio podem ter lógica sem poluição de ORM         | Overhead de manutenção em projetos pequenos                      |
| Testes unitários usam fakes simples (listas/dicts em memória)     | Performance de mapeamento em listas grandes (N+1 potencial)      |

### Domínio vs ORM — comparação lado a lado

**Entidade de domínio** (`app/modules/auth/domain/entities.py:8`):

```python
@dataclass(kw_only=True)
class User:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: EmailAddress
    hashed_password: HashedPassword
    is_active: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def deactivate(self):
        self.is_active = False

    def activate(self):
        self.is_active = True
```

**Modelo ORM** (`app/modules/auth/infrastructure/orm_models.py:9`):

```python
class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

**Diferenças notáveis**:
1. `id` é `uuid.UUID` no domínio, mas `str` no ORM (SQLite não tem tipo UUID nativo)
2. `email` é `EmailAddress` (value object) no domínio, mas `str` no ORM
3. `hashed_password` é `HashedPassword` (value object) no domínio, mas `str` no ORM
4. A entidade de domínio tem métodos de comportamento (`deactivate`, `activate`); a
   ORM não
5. A entidade de domínio é um `@dataclass` puro; a ORM herda de `DeclarativeBase`

### Mapeamento bidirecional no repositório

**Exemplo completo — `SQLAlchemyUserRepository`** (`app/modules/auth/infrastructure/repositories.py`):

```python
class SQLAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_orm(self, user: User) -> UserORM:
        return UserORM(
            id=str(user.id),
            email=user.email.address,                 # Extrai de value object
            hashed_password=user.hashed_password.hash_passwd,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    def _to_domain(self, orm: UserORM) -> User:
        return User(
            id=uuid.UUID(orm.id),
            email=EmailAddress(orm.email),             # Reconstrói value object
            hashed_password=HashedPassword(orm.hashed_password),
            is_active=orm.is_active,
            created_at=orm.created_at,
        )

    def save(self, user: User) -> User:
        orm = self._to_orm(user)
        self.session.merge(orm)                        # Upsert
        self.session.commit()
        return self._to_domain(orm)
```

---

## Entities / Models Existentes

| Entidade ORM   | Tabela          | Módulo | Relacionamentos                         |
|----------------|-----------------|--------|-----------------------------------------|
| `UserORM`      | `users`         | auth   | Nenhum (independente)                   |
| `TodoListORM`  | `todo_lists`    | todo   | `hasMany: TodoItemORM` (cascade delete) |
| `TodoItemORM`  | `todo_items`    | todo   | `belongsTo: TodoListORM`                |

### Schema completo do banco

```sql
-- users
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at DATETIME NOT NULL
);

-- todo_lists
CREATE TABLE todo_lists (
    id VARCHAR PRIMARY KEY,
    owner_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);

-- todo_items
CREATE TABLE todo_items (
    id VARCHAR PRIMARY KEY,
    todo_list_id VARCHAR NOT NULL REFERENCES todo_lists(id),
    title VARCHAR NOT NULL,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL
);
```

---

## Migrations

### Ferramenta

**Alembic** — ferramenta de migração oficial do SQLAlchemy.

### Localização

```
app/
├── alembic.ini                  ← Configuração (sqlalchemy.url, script_location)
└── alembic/
    ├── env.py                   ← Environment (target_metadata = Base.metadata)
    ├── script.py.mako           ← Template de migration
    └── versions/
        ├── cfba94646eec_create_users_table.py
        └── 2693906b62e5_create_todo_tables.py
```

### Configuração do Alembic

`alembic/env.py` importa todos os modelos ORM e usa `Base.metadata` como target:

```python
from modules.auth.infrastructure.orm_models import UserORM
from modules.todo.infrastructure.orm_models import TodoItemORM, TodoListORM
from shared.base_model import Base

target_metadata = Base.metadata
```

O `alembic.ini` define a URL de conexão (SQLite padrão):

```ini
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///./todo_app.db
```

### Comandos

```bash
cd app

# Criar nova migration automaticamente a partir dos modelos ORM
alembic revision --autogenerate -m "descricao da migration"

# Aplicar todas as migrations pendentes
alembic upgrade head

# Reverter uma migration
alembic downgrade -1

# Ver histórico
alembic history
```

### Estratégia de versionamento

As migrations seguem o padrão do Alembic: cada arquivo tem um `revision` (hash único) e
um `down_revision` que aponta para a migration anterior, formando uma cadeia linear:

```
None ← cfba94646eec (users) ← 2693906b62e5 (todo_lists + todo_items)
```

### Migrations existentes

**1. `cfba94646eec` — `create_users_table`**

```python
def upgrade():
    op.create_table("users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
```

**2. `2693906b62e5` — `create_todo_tables`**

```python
def upgrade():
    op.create_table("todo_lists",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table("todo_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("todo_list_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["todo_list_id"], ["todo_lists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
```

---

## Repositories — Padrão Aplicado

### Visão geral

O padrão Repository é aplicado com a seguinte separação:

| Camada         | Artefato                                        | Papel                        |
|----------------|-------------------------------------------------|------------------------------|
| **Domain**     | `UserRepositoryPort(ABC)`, `TodoListRepositoryPort(ABC)` | Interface (port) — define o contrato |
| **Infrastructure** | `SQLAlchemyUserRepository`, `SQLAlchemyTodoListRepository` | Implementação concreta (adapter) |

O use case depende APENAS da interface (port), nunca da implementação concreta. A
resolução concreta ocorre no controller (route handler), que instancia o repositório
com a `Session` do SQLAlchemy.

### Exemplo: interface no domain

`app/modules/todo/domain/ports.py`:

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

### Exemplo: implementação na infrastructure

`app/modules/todo/infrastructure/repositories.py` — o método `save()` é o mais complexo
pois lida com a persistência do agregado `TodoList` + `TodoItem`:

```python
def save(self, todo_list: TodoList) -> TodoList:
    list_id = str(todo_list.id)
    orm = self._list_to_orm(todo_list)

    # Estratégia: delete-and-reinsert para itens do agregado
    self.session.query(TodoItemORM).filter_by(todo_list_id=list_id).delete()
    self.session.merge(orm)

    item_orms = [self._item_to_orm(item, list_id) for item in todo_list.items]
    self.session.add_all(item_orms)
    self.session.commit()

    saved = self.session.get(TodoListORM, list_id)
    return self._list_to_domain(saved)
```

**Estratégia de persistência do agregado**: Como `TodoList` é um aggregate root que
contém uma coleção de `TodoItem`, o método `save` adota a estratégia **delete-all +
reinsert** para itens:
1. Remove todos os `todo_items` vinculados à lista
2. Faz merge do registro `todo_lists`
3. Insere todos os itens atuais do agregado

Isso garante consistência do agregado (nenhum item "fantasma" permanece), mas tem o
custo de executar múltiplas queries por save. Para aplicações com muitas operações
concorrentes, uma estratégia de diff seria mais eficiente.

---

## Transações

### Abordagem: Implícita por sessão

O projeto **não implementa um padrão Unit of Work** explícito. Em vez disso, utiliza
transações implícitas do SQLAlchemy:

- Cada método do repositório chama `self.session.commit()` explicitamente
- A sessão é criada por requisição (`get_db()`) e fechada ao final
- Cada operação de repositório é uma transação independente

**Exemplo — commit explícito no repositório de usuários:**

```python
def save(self, user: User) -> User:
    orm = self._to_orm(user)
    self.session.merge(orm)
    self.session.commit()          # Transação implícita
    return self._to_domain(orm)
```

**Exemplo — commit no repositório de tarefas (mais complexo, múltiplas operações):**

```python
def save(self, todo_list: TodoList) -> TodoList:
    # ...
    self.session.query(TodoItemORM).filter_by(todo_list_id=list_id).delete()
    self.session.merge(orm)
    self.session.add_all(item_orms)
    self.session.commit()          # Todas as operações em uma transação
    # ...
```

> ⚠️ **Limitação identificada**: Se um use case precisar de múltiplas operações de
> repositório em uma única transação (ex: criar usuário + criar lista padrão), não há
> mecanismo para isso no código atual. Cada `save()` faz seu próprio `commit()`. Para
> cenários transacionais, seria necessário um gerenciador de transação no nível do use
> case (Unit of Work).

---

## Queries Complexas

### Situação atual

O projeto não contém queries complexas (JOINs multi-tabela, subqueries, agregações ou
raw SQL). Todas as queries são queries simples do SQLAlchemy ORM:

- `session.query(UserORM).filter_by(email=email).first()`
- `session.query(TodoListORM).filter_by(owner_id=owner_id).all()`
- `session.get(TodoListORM, list_id)`

O carregamento de `TodoList` faz eager loading implícito dos itens via o relacionamento
`items: Mapped[list[TodoItemORM]]`, o que gera um JOIN automaticamente quando o atributo
é acessado (lazy loading padrão do SQLAlchemy).

> ⚠️ **Possível problema N+1**: Na rota `GET /lists/`, o método
> `find_all_by_owner` carrega todas as listas, e para cada lista o relacionamento
> `items` é carregado sob demanda (lazy load). Com SQLite isso não é crítico, mas com
> PostgreSQL em produção poderia causar queries N+1. A solução seria usar
> `selectinload` ou `joinedload` no repositório.

---

[← Voltar ao Index](./index.md)
