# Arquitetura Hexagonal — Visão Aplicada ao Projeto

## Índice

- [O que é Arquitetura Hexagonal (Ports & Adapters)](#o-que-é-arquitetura-hexagonal-ports--adapters)
- [Como o Projeto Implementa Cada Camada](#como-o-projeto-implementa-cada-camada)
  - [Domain (Núcleo)](#domain-núcleo)
  - [Application (Casos de Uso)](#application-casos-de-uso)
  - [Infrastructure (Adapters de Saída)](#infrastructure-adapters-de-saída)
  - [Interface (Adapters de Entrada)](#interface-adapters-de-entrada)
- [Fluxo de uma Requisição (End-to-End)](#fluxo-de-uma-requisição-end-to-end)
- [Organização dos Módulos (Monolito Modular)](#organização-dos-módulos-monolito-modular)
- [Injeção de Dependência](#injeção-de-dependência)

---

## O que é Arquitetura Hexagonal (Ports & Adapters)

A Arquitetura Hexagonal, proposta por Alistair Cockburn em 2005, é um padrão arquitetural
que visa isolar o núcleo da aplicação (lógica de negócio) dos detalhes de infraestrutura
(banco de dados, frameworks web, APIs externas). O princípio central é a **inversão de
dependência**: o domínio define interfaces (`ports`) que representam o que ele precisa do
mundo externo, e as implementações concretas (`adapters`) são injetadas em tempo de
execução, sem que o domínio jamais dependa de código externo.

### Por que foi escolhida para este projeto

O propósito explícito do projeto é ser "overengineered" — ou seja, demonstrar padrões
arquiteturais avançados como exercício educacional. A Arquitetura Hexagonal foi adotada
para:

1. **Separar claramente** regras de negócio de framework e infraestrutura
2. **Permitir testes unitários** do domínio com fakes (sem subir banco ou servidor)
3. **Demonstrar DIP (Dependency Inversion Principle)** com ports e adapters
4. **Viabilizar troca de infraestrutura** (ex: trocar SQLite por PostgreSQL sem alterar
   o domínio)
5. **Organizar o código** em módulos com responsabilidades bem definidas

### Diagrama conceitual

```
┌─────────────────────────────────────────────────────────────┐
│                       INTERFACES                            │  ← Adaptadores de Entrada
│               (FastAPI Routers, Pydantic Schemas)           │    HTTP REST
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   APPLICATION                       │   │  ← Casos de Uso
│   │   (Use Cases: RegisterUser, CreateTodoList, etc.)   │   │    Orquestração
│   │   ┌─────────────────────────────────────────────┐   │   │
│   │   │                DOMAIN                       │   │   │  ← Núcleo / Regras
│   │   │  (Entities, Value Objects, Domain Services, │   │   │    Sem dependências
│   │   │   Ports/Interfaces, Domain Exceptions)      │   │   │    externas
│   │   └─────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────┘   │
│                    INFRASTRUCTURE                           │  ← Adaptadores de Saída
│    (SQLAlchemy Repositories, bcrypt Hasher, JWT Provider)   │    Banco, Cripto, Token
└─────────────────────────────────────────────────────────────┘
```

As setas de dependência **sempre apontam para dentro**:
- `Interface → Application → Domain`
- `Infrastructure → Domain` (implementa ports definidos no domain)
- `Domain` **não depende de ninguém** (zero imports de framework, ORM, HTTP)

---

## Como o Projeto Implementa Cada Camada

### Domain (Núcleo)

O domain é a camada mais interna e contém:

- **Entidades** (`User`, `TodoList`, `TodoItem`): dataclasses Python puras com métodos de
  negócio. Contêm identidade (`id: UUID`) e encapsulam regras de estado.
- **Value Objects** (`EmailAddress`, `HashedPassword`, `ListName`): dataclasses imutáveis
  (`frozen=True`) com validação no construtor. Não possuem identidade própria.
- **Ports** (`UserRepositoryPort`, `TodoListRepositoryPort`, `PasswordHasher`,
  `TokenProvider`): classes abstratas (ABC) que definem contratos que a infraestrutura
  deve cumprir.
- **Domain Services** (`AuthenticationService`): lógica que não pertence naturalmente a
  uma única entidade.
- **Domain Exceptions**: exceções específicas do domínio, separadas das exceções HTTP.

**O que NUNCA entra aqui**: imports de FastAPI, SQLAlchemy, bcrypt, PyJWT, ou qualquer
framework/biblioteca externa. As entidades não têm decorators de ORM nem dependem de
configuração alguma.

**Exemplo real — Entidade `TodoList`** (`app/modules/todo/domain/entities.py:38`):

```python
@dataclass(kw_only=True)
class TodoList:
    name: ListName
    owner_id: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    items: list[TodoItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def verify_ownership(self, user_id: str):
        if self.owner_id != user_id:
            raise AccessDeniedError()

    def add_item(self, title: str) -> TodoItem:
        if not title.strip():
            raise EmptyTitleError()
        item = TodoItem(title=title)
        self.items.append(item)
        return item
```

**Exemplo real — Port (interface)** (`app/modules/auth/domain/ports.py:6`):

```python
class UserRepositoryPort(ABC):
    @abstractmethod
    def save(self, user: User) -> User: ...
    @abstractmethod
    def find_by_email(self, email: str) -> User | None: ...
    @abstractmethod
    def find_by_id(self, user_id: str) -> User | None: ...
```

### Application (Casos de Uso)

A camada de application contém os **use cases** (casos de uso). Cada use case é uma classe
com um único método público `execute()` que orquestra entidades de domínio e repositórios.
Não contém regras de negócio — delega para as entidades do domain.

**Padrão seguido por todos os use cases:**

1. Recebe dependências via **construtor** (`repo: UserRepositoryPort`, etc.)
2. No método `execute()`, carrega entidades via repositório
3. Chama métodos de domínio nas entidades
4. Persiste via repositório
5. Retorna resultado (entidade de domínio ou DTO simples)

**Exemplo real — `AddTodoItemUseCase`** (`app/modules/todo/application/use_cases.py:30`):

```python
class AddTodoItemUseCase:
    def __init__(self, repo: TodoListRepositoryPort) -> None:
        self._repo = repo

    def execute(self, list_id: str, title: str, user_id: str) -> TodoList:
        todo_list = self._get_list_or_raise(list_id)
        todo_list.verify_ownership(user_id)       # regra de domínio
        todo_list.add_item(title)                  # regra de domínio
        return self._repo.save(todo_list)          # persistência

    def _get_list_or_raise(self, list_id: str) -> TodoList:
        todo_list = self._repo.find_by_id(list_id)
        if todo_list is None:
            raise TodoListNotFoundError(list_id)
        return todo_list
```

**Nota sobre DTOs**: Neste projeto, os use cases não definem DTOs formais de
entrada/saída — recebem parâmetros primitivos e retornam diretamente as entidades de
domínio. A transformação para JSON ocorre nos controllers da camada de interface.

### Infrastructure (Adapters de Saída)

Contém as implementações concretas das interfaces definidas no domain. Aqui ficam:

- **Repositórios ORM**: implementam `*RepositoryPort` usando SQLAlchemy
- **Provedores de hash**: implementam `PasswordHasher` usando bcrypt
- **Provedores de token**: implementam `TokenProvider` usando PyJWT
- **Modelos ORM**: classes SQLAlchemy com `DeclarativeBase`, decorators e relacionamentos

**Separação crucial — Persistence Model vs Domain Model**: As entidades ORM
(`UserORM`, `TodoListORM`, `TodoItemORM`) são **totalmente separadas** das entidades de
domínio (`User`, `TodoList`, `TodoItem`). Os repositórios fazem mapeamento explícito nos
dois sentidos via métodos privados `_to_orm()` e `_to_domain()`.

**Exemplo real — Mapeamento domain ↔ ORM** (`app/modules/todo/infrastructure/repositories.py:18`):

```python
# Domain → ORM
def _item_to_orm(self, item: TodoItem, list_id: str) -> TodoItemORM:
    return TodoItemORM(
        id=str(item.id),
        todo_list_id=list_id,
        title=item.title,
        is_completed=item.completed,       # Nota: atributo renomeado
    )

# ORM → Domain
def _item_to_domain(self, orm: TodoItemORM) -> TodoItem:
    return TodoItem(
        id=uuid.UUID(orm.id),
        title=orm.title,
        completed=orm.is_completed,        # Mapeamento inverso
        created_at=orm.created_at,
    )
```

### Interface (Adapters de Entrada)

Contém os adapters de entrada — os mecanismos que permitem ao mundo externo interagir
com o sistema. Neste projeto, a única interface externa é HTTP REST via FastAPI.

**Princípio**: Os route handlers (controllers) **não contêm lógica de negócio**. Sua
única responsabilidade é:

1. Extrair e validar dados da requisição (via Pydantic)
2. Instanciar dependências (repositórios, providers)
3. Criar e executar o use case
4. Mapear exceções de domínio para códigos HTTP
5. Serializar a resposta

**Exemplo real — endpoint de login** (`app/modules/auth/interface/router.py:42`):

```python
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    repo = SQLAlchemyUserRepository(db)
    hasher = BcryptPasswordHasher()
    token_provider = PyJWTTokenProvider()
    use_case = LoginUseCase(repo=repo, hasher=hasher, token_provider=token_provider)

    try:
        token = use_case.execute(email=body.email, password=body.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(access_token=token)
```

---

## Fluxo de uma Requisição (End-to-End)

### Exemplo: `POST /auth/login`

```
Cliente HTTP
  │
  │  POST /auth/login { "email": "user@ex.com", "password": "123" }
  ▼
──────────────────────────────── Interface (AuthRouter) ────────────────────────
  │  FastAPI valida body contra LoginRequest (Pydantic)
  │  FastAPI injeta db: Session via Depends(get_db)
  │  Controller instancia manualmente:
  │    repo = SQLAlchemyUserRepository(db)
  │    hasher = BcryptPasswordHasher()
  │    token_provider = PyJWTTokenProvider()
  │
  ▼
──────────────────────────────── Application ───────────────────────────────────
  │  LoginUseCase.execute(email, password)
  │    1. Busca User via repo.find_by_email(email)
  │    2. Se não encontrado → InvalidCredentialsError
  │    3. Verifica senha via hasher.verify(password, user.hashed_password)
  │    4. Se inválida → InvalidCredentialsError
  │    5. Gera token via token_provider.generate({"sub": str(user.id)})
  │  Retorna token JWT (string)
  │
  ▼
──────────────────────────────── Infrastructure ────────────────────────────────
  │  SQLAlchemyUserRepository.find_by_email()
  │    → session.query(UserORM).filter_by(email=email).first()
  │    → Converte UserORM → User (domain) via _to_domain()
  │
  │  BcryptPasswordHasher.verify()
  │    → bcrypt.checkpw(plain, hashed)
  │
  │  PyJWTTokenProvider.generate()
  │    → jwt.encode(payload, secret, algorithm="HS256")
  │    → Adiciona claims iat (issued at) e exp (expiration)
  │
  ▼
──────────────────────────────── Database ──────────────────────────────────────
  │  SELECT * FROM users WHERE email = ?
  ▼
──────────────────────────────── Interface (Resposta) ──────────────────────────
  │  Controller captura token, retorna TokenResponse(access_token=token)
  │  FastAPI serializa para JSON
  ▼
HTTP 200 { "access_token": "eyJ...", "token_type": "bearer" }
```

---

## Organização dos Módulos (Monolito Modular)

### O que é um Monolito Modular

Um **monolito modular** é uma aplicação que roda como um único processo (single
deployable), mas com código organizado em módulos independentes com fronteiras bem
definidas. Diferente do monolito tradicional (onde tudo é acoplado) e dos microserviços
(onde cada módulo é um deploy independente), o monolito modular oferece:

- **Baixa complexidade operacional** (um único deploy)
- **Alta coesão interna** (cada módulo tem seu próprio domain/application/infrastructure/interface)
- **Fronteiras explícitas** (comunicação via interfaces, não via imports diretos)

### Estrutura de diretórios

```
app/
├── main.py              ← Ponto de entrada FastAPI, registro de rotas
├── shared/              ← Código compartilhado (transversal)
│   ├── base_model.py    ← SQLAlchemy DeclarativeBase
│   ├── config.py        ← Pydantic Settings (.env)
│   ├── database.py      ← Engine, Session, get_db()
│   ├── dependencies.py  ← get_current_user_id (JWT auth Depends)
│   └── exceptions.py    ← AppError, NotFoundError, AccessDeniedError, etc.
├── modules/
│   ├── auth/            ← Módulo de autenticação
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   ├── adapters/    ← (vazio — placeholder)
│   │   └── interface/
│   └── todo/            ← Módulo de tarefas
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       ├── adapters/    ← (vazio — placeholder)
│       └── interface/
└── tests/
    ├── auth/
    │   ├── unit/
    │   └── integration/
    └── todo/
        ├── unit/
        └── integration/
```

### Como os módulos se comunicam

- **Auth → Todo**: O módulo `todo` depende de auth apenas para autenticação, via a
  dependência `get_current_user_id()` definida em `shared/dependencies.py`, que por sua
  vez usa classes do módulo auth (`PyJWTTokenProvider`, `InvalidTokenError`,
  `TokenExpiredError`). O `user_id` extraído do JWT é passado como parâmetro para os use
  cases do módulo todo.

- **Módulo → Shared**: Ambos os módulos (`auth` e `todo`) dependem de `shared/` para:
  - `Base` (classe base SQLAlchemy) para seus modelos ORM
  - `get_db()` (sessão de banco) em seus route handlers
  - `AppError` como base para algumas exceções globais

### Regras de dependência entre módulos

1. **Módulos de feature NÃO devem depender diretamente entre si** — a comunicação entre
   bounded contexts deve ocorrer via interfaces ou código compartilhado em `shared/`.
   Neste projeto, `todo` não importa diretamente nada do domain/application do `auth`.

2. **Todos os módulos PODEM depender de `shared/`** — o pacote `shared` contém apenas
   concerns transversais que não pertencem a nenhum domínio específico (configuração,
   conexão com banco, autenticação HTTP).

3. **Nenhum módulo de feature pode depender da `interface/` de outro módulo** — rotas
   são privadas ao módulo.

> ⚠️ **Exceção identificada**: `shared/dependencies.py` (linha 7) importa
> `modules.auth.infrastructure.jwt_provider.PyJWTTokenProvider`, o que é uma violação
> leve da regra de dependência (shared não deveria depender de um módulo específico).
> O ideal seria definir a lógica de autenticação como um middleware no módulo auth ou
> injetar o `TokenProvider` via DI.

---

## Injeção de Dependência

### Estratégia: Manual Constructor Injection (Pure DI)

O projeto **NÃO utiliza nenhum contêiner de IoC** (como `dependency-injector` ou
`inject`). A injeção de dependência é feita manualmente:

1. **Use cases** recebem dependências via **construtor** (padrão Constructor Injection)
2. **Route handlers** instanciam manualmente todas as dependências e as conectam
3. **FastAPI DI** é usado **apenas** para prover `db: Session` via `Depends(get_db)`
   e `user_id: UUID` via `Depends(get_current_user_id)`

### Exemplo de wiring manual

```python
# No route handler (interface/auth/router.py)
@router.post("/register", ...)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    repo = SQLAlchemyUserRepository(db)         # Adapter concreto
    hasher = BcryptPasswordHasher()             # Adapter concreto
    use_case = RegisterUserUseCase(             # Caso de uso
        repo=repo,                              # Recebe interface (polimorfismo)
        hasher=hasher
    )
    user = use_case.execute(email=body.email, password=body.password)
```

### Tradeoff

**Vantagem**: Explicitude máxima — é fácil rastrear quais dependências cada componente
usa e como são construídas. Nenhum "mágica" de framework de DI.

**Desvantagem**: Repetição de código — cada route handler repete as mesmas linhas de
instanciação de repositórios, hashers e token providers. Em um projeto maior, isso
justificaria a introdução de um contêiner de DI ou factories.

---

[← Voltar ao Index](./index.md)
