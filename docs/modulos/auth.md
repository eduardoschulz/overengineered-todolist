# Módulo: Auth

> **Responsabilidade:** Registro de novos usuários, autenticação por email/senha e
> emissão de tokens JWT para controle de acesso.

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

O módulo `auth` é o bounded context responsável pela **identidade e autenticação** dos
usuários do sistema. Ele implementa o ciclo completo de registro e login, gerando tokens
JWT que são posteriormente usados pelo módulo `todo` para autorização.

O módulo segue estritamente a Arquitetura Hexagonal com as 4 camadas (domain, application,
infrastructure, interface), usando separação total entre entidades de domínio e modelos
ORM, e injeção manual de dependências nos route handlers.

**Tecnologias específicas deste módulo:**

- **bcrypt**: Hash e verificação de senhas (função lenta, resistente a força bruta)
- **PyJWT**: Geração e decodificação de tokens JWT (HS256, claims `iat` e `exp`)
- **Pydantic `EmailStr`**: Validação de formato de email na camada de interface

---

## Estrutura de Diretórios

```
app/modules/auth/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py                  ← User (entidade de domínio)
│   ├── value_objects.py             ← EmailAddress, HashedPassword
│   ├── ports.py                     ← UserRepositoryPort, PasswordHasher, TokenProvider (ABCs)
│   ├── exceptions.py                ← InvalidCredentialsError, EmailAlreadyExistsError, etc.
│   └── authentication_service.py    ← AuthenticationService (domain service)
├── application/
│   ├── __init__.py
│   └── use_cases.py                 ← RegisterUserUseCase, LoginUseCase
├── infrastructure/
│   ├── __init__.py
│   ├── orm_models.py                ← UserORM (SQLAlchemy model)
│   ├── repositories.py              ← SQLAlchemyUserRepository
│   ├── bcrypt_hasher.py             ← BcryptPasswordHasher
│   └── jwt_provider.py              ← PyJWTTokenProvider
├── adapters/
│   └── __init__.py                  ← (vazio — placeholder)
└── interface/
    ├── router.py                    ← POST /auth/register, POST /auth/login
    └── schemas.py                   ← RegisterRequest, LoginRequest, TokenResponse, UserResponse
```

---

## Domain

### Responsabilidade da Camada de Domain

A camada de domain do módulo `auth` define o que é um **usuário** no sistema, as regras
de validação de email e senha, os contratos que a infraestrutura deve implementar e as
exceções específicas do domínio de autenticação. Não há dependências de framework, ORM ou
bibliotecas externas.

### Entidades

#### `User`

**Arquivo:** `app/modules/auth/domain/entities.py`

**Descrição:** Representa um usuário registrado no sistema. Possui identidade única
(UUID v4), email validado, senha já hasheada e estado ativo/inativo.

**Propriedades:**

| Propriedade       | Tipo             | Descrição                                    |
|-------------------|------------------|----------------------------------------------|
| `id`              | `uuid.UUID`      | Identificador único (UUID4)                  |
| `email`           | `EmailAddress`   | Email do usuário (value object com validação)|
| `hashed_password` | `HashedPassword` | Hash bcrypt da senha (value object imutável) |
| `is_active`       | `bool`           | Estado de ativação do usuário                |
| `created_at`      | `datetime`       | Data/hora de criação (UTC)                   |

**Regras de Negócio / Invariantes:**

- Email deve conter `@` (validado pelo value object `EmailAddress`)
- Senha nunca é armazenada em plain text — sempre hasheada antes de criar a entidade
- Um usuário pode ser desativado/ativado via `deactivate()`/`activate()`
- Um usuário pode trocar de email ou senha via `change_email()`/`change_password()`

**Código completo:**

```python
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .value_objects import EmailAddress, HashedPassword

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

    def change_email(self, new_email: EmailAddress):
        self.email = new_email

    def change_password(self, new_hashed_password: HashedPassword):
        self.hashed_password = new_hashed_password
```

### Value Objects

#### `EmailAddress`

**Arquivo:** `app/modules/auth/domain/value_objects.py`

**Descrição:** Representa um endereço de email válido. É imutável (`frozen=True`) e
valida no construtor que o valor contém `@`. Como value object, não possui identidade
própria e é comparado por valor.

```python
@dataclass(frozen=True)
class EmailAddress:
    address: str

    def __post_init__(self):
        if "@" not in self.address:
            raise ValueError(f"Invalid email: {self.address}")
```

#### `HashedPassword`

**Arquivo:** `app/modules/auth/domain/value_objects.py`

**Descrição:** Wrapper imutável para o hash bcrypt da senha. Garante que o hash nunca é
confundido com uma senha plain text. Não contém lógica de hash — o hashing é
responsabilidade da infraestrutura.

```python
@dataclass(frozen=True)
class HashedPassword:
    hash_passwd: str
```

### Domain Services

#### `AuthenticationService`

**Arquivo:** `app/modules/auth/domain/authentication_service.py`

**Descrição:** Serviço de domínio que coordena a autenticação de um usuário, combinando
o repositório (busca do usuário), o hasher (verificação de senha) e o token provider
(geração do JWT). É uma lógica que não pertence naturalmente a uma única entidade.

> ⚠️ **Duplicação identificada**: Este serviço **não é utilizado** pelos use cases.
> O `LoginUseCase` (em `application/use_cases.py`) replica a mesma lógica de
> autenticação. Isso representa uma oportunidade de refatoração.

```python
class AuthenticationService:
    def __init__(self, repo: UserRepositoryPort, hasher: PasswordHasher,
                 token_provider: TokenProvider) -> None:
        self._repo = repo
        self._hasher = hasher
        self._token_provider = token_provider

    def authenticate(self, email: str, password: str) -> str:
        user = self._repo.find_by_email(email)
        if user is None:
            raise InvalidCredentialsError("Invalid email or password")
        if not self._hasher.verify(password, user.hashed_password.hash_passwd):
            raise InvalidCredentialsError("Invalid email or password")
        return self._token_provider.generate({"sub": str(user.id)})
```

### Domain Exceptions

**Arquivo:** `app/modules/auth/domain/exceptions.py`

Exceções específicas do domínio de autenticação — separadas das exceções HTTP e das
exceções globais de `shared/exceptions.py`:

```python
class InvalidTokenError(Exception):
    """Token JWT inválido (assinatura, formato, etc.)"""
    pass

class TokenExpiredError(InvalidTokenError):
    """Token JWT expirado (claim exp vencida)"""
    pass

class EmailAlreadyExistsError(Exception):
    """Email já cadastrado — conflito no registro"""
    pass

class InvalidCredentialsError(Exception):
    """Credenciais inválidas (email não encontrado ou senha incorreta)"""
    pass
```

> 💡 **Nota**: `InvalidTokenError` e `TokenExpiredError` são importadas em
> `shared/dependencies.py` para o middleware de autenticação JWT.

---

## Application

### Responsabilidade da Camada de Application

A camada de application contém os use cases que orquestram as operações de registro e
login. Eles não contêm lógica de negócio — apenas coordenam entidades de domínio e ports
de infraestrutura.

### Use Cases

#### `RegisterUserUseCase`

**Arquivo:** `app/modules/auth/application/use_cases.py`

**Descrição:** Registra um novo usuário no sistema. Verifica unicidade de email, hasheia
a senha e persiste a entidade.

**Input:** `email: str`, `password: str`
**Output:** `User` (entidade de domínio recém-criada)

**Fluxo interno:**
1. Verifica se email já existe via `repo.find_by_email(email)`
2. Se existir, lança `EmailAlreadyExistsError`
3. Hasheia a senha via `hasher.hash(password)`
4. Cria entidade `User` com `EmailAddress`, `HashedPassword` e `is_active=True`
5. Persiste via `repo.save(user)`
6. Retorna o `User` persistido

```python
class RegisterUserUseCase:
    def __init__(self, repo: UserRepositoryPort, hasher: PasswordHasher) -> None:
        self._repo = repo
        self._hasher = hasher

    def execute(self, email: str, password: str) -> User:
        if self._repo.find_by_email(email):
            raise EmailAlreadyExistsError(f"User with email {email} already exists")
        hashed = self._hasher.hash(password)
        user = User(
            email=EmailAddress(email),
            hashed_password=HashedPassword(hashed),
            is_active=True,
        )
        return self._repo.save(user)
```

#### `LoginUseCase`

**Arquivo:** `app/modules/auth/application/use_cases.py`

**Descrição:** Autentica um usuário por email e senha e retorna um token JWT. Equivalente
funcional ao `AuthenticationService.authenticate()` (duplicação identificada).

**Input:** `email: str`, `password: str`
**Output:** `str` (token JWT)

**Fluxo interno:**
1. Busca usuário via `repo.find_by_email(email)`
2. Se não encontrado, lança `InvalidCredentialsError`
3. Verifica senha via `hasher.verify(password, user.hashed_password.hash_passwd)`
4. Se inválida, lança `InvalidCredentialsError`
5. Gera token JWT via `token_provider.generate({"sub": str(user.id)})`
6. Retorna o token

```python
class LoginUseCase:
    def __init__(self, repo: UserRepositoryPort, hasher: PasswordHasher,
                 token_provider: TokenProvider) -> None:
        self._repo = repo
        self._hasher = hasher
        self._token_provider = token_provider

    def execute(self, email: str, password: str) -> str:
        user = self._repo.find_by_email(email)
        if user is None:
            raise InvalidCredentialsError("Invalid email or password")
        if not self._hasher.verify(password, user.hashed_password.hash_passwd):
            raise InvalidCredentialsError("Invalid email or password")
        return self._token_provider.generate({"sub": str(user.id)})
```

### Ports (Interfaces definidas pelo módulo)

Além do `UserRepositoryPort`, o módulo auth define mais duas interfaces de
infraestrutura:

**`PasswordHasher`** (`app/modules/auth/domain/ports.py:20`):

```python
class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_password: str) -> str: ...
    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool: ...
```

Motivação: Isolar o algoritmo de hash (bcrypt) para poder trocá-lo no futuro (ex: argon2)
sem alterar o domínio.

**`TokenProvider`** (`app/modules/auth/domain/ports.py:30`):

```python
class TokenProvider(ABC):
    @abstractmethod
    def generate(self, payload: dict) -> str: ...
    @abstractmethod
    def decode(self, token: str) -> dict: ...
```

Motivação: Isolar a implementação de JWT (PyJWT) para poder trocar a biblioteca ou
algoritmo (ex: RS256) sem alterar o domínio.

---

## Infrastructure

### Responsabilidade da Camada de Infrastructure

Implementações concretas dos ports definidos no domain. Aqui residem dependências de
bibliotecas externas (SQLAlchemy, bcrypt, PyJWT), encapsuladas atrás das interfaces.

### ORM Entity

#### `UserORM`

**Arquivo:** `app/modules/auth/infrastructure/orm_models.py`

**Tabela mapeada:** `users`

```python
class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

Notas:
- `id` é armazenado como `String` porque SQLite não tem tipo UUID nativo
- Não há relacionamentos — `users` é uma tabela independente

### Repositório (Implementação Concreta)

#### `SQLAlchemyUserRepository` → implementa `UserRepositoryPort`

**Arquivo:** `app/modules/auth/infrastructure/repositories.py`

**ORM usado internamente:** SQLAlchemy 2.x (Session)

```python
class SQLAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_orm(self, user: User) -> UserORM:
        return UserORM(
            id=str(user.id),
            email=user.email.address,
            hashed_password=user.hashed_password.hash_passwd,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    def _to_domain(self, orm: UserORM) -> User:
        return User(
            id=uuid.UUID(orm.id),
            email=EmailAddress(orm.email),
            hashed_password=HashedPassword(orm.hashed_password),
            is_active=orm.is_active,
            created_at=orm.created_at,
        )

    def save(self, user: User) -> User:
        orm = self._to_orm(user)
        self.session.merge(orm)
        self.session.commit()
        return self._to_domain(orm)

    def find_by_email(self, email: str) -> User | None:
        orm = self.session.query(UserORM).filter_by(email=email).first()
        if orm is None:
            return None
        return self._to_domain(orm)

    def find_by_id(self, user_id: str) -> User | None:
        orm = self.session.query(UserORM).get(user_id)
        if orm is None:
            return None
        return self._to_domain(orm)
```

**Como persiste os dados**: Usa `session.merge()` para upsert — se o registro já existe
(mesmo ID), atualiza; se não, insere. Após o merge, faz `commit()` e retorna a entidade
de domínio reconstruída a partir do estado persistido.

### Providers de Infraestrutura

#### `BcryptPasswordHasher`

**Arquivo:** `app/modules/auth/infrastructure/bcrypt_hasher.py`

**Implementa:** `PasswordHasher` (port do domain)
**Tecnologia:** bcrypt (biblioteca `bcrypt`)

```python
class BcryptPasswordHasher(PasswordHasher):
    def hash(self, plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
```

#### `PyJWTTokenProvider`

**Arquivo:** `app/modules/auth/infrastructure/jwt_provider.py`

**Implementa:** `TokenProvider` (port do domain)
**Tecnologia:** PyJWT (`jwt` package)

```python
class PyJWTTokenProvider(TokenProvider):
    def generate(self, payload: dict) -> str:
        now = datetime.now(timezone.utc)
        payload["iat"] = now
        payload["exp"] = now + timedelta(minutes=settings.JWT_TTL_MINUTES)
        return jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )

    def decode(self, token: str) -> dict:
        try:
            return jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError
        except jwt.InvalidTokenError:
            raise InvalidTokenError
```

**Claims do JWT:**

| Claim | Significado            | Origem                        |
|-------|------------------------|-------------------------------|
| `sub` | Subject (ID do usuário)| Passado via `payload["sub"]`  |
| `iat` | Issued At (emitido em) | `datetime.now(timezone.utc)`  |
| `exp` | Expiration (expira em) | `iat + JWT_TTL_MINUTES`       |

O `decode` traduz exceções da biblioteca PyJWT para exceções de domínio
(`TokenExpiredError`, `InvalidTokenError`), mantendo o domínio isolado da biblioteca.

---

## Interface

### Responsabilidade da Camada de Interface

Expõe as operações de registro e login como endpoints HTTP REST via FastAPI. Os
controllers são funções simples que:
1. Validam o corpo da requisição via Pydantic
2. Instanciam manualmente as dependências
3. Executam o use case
4. Capturam exceções de domínio e as traduzem para HTTP
5. Serializam a resposta

### Rotas expostas

| Método | Path            | Use Case              | Auth requerida | Resposta (sucesso) |
|--------|-----------------|-----------------------|----------------|---------------------|
| POST   | `/auth/register`| `RegisterUserUseCase` | Não            | 201 + `UserResponse`|
| POST   | `/auth/login`   | `LoginUseCase`        | Não            | 200 + `TokenResponse`|

### Schemas (DTOs de Interface)

**Arquivo:** `app/modules/auth/interface/schemas.py`

```python
class RegisterRequest(BaseModel):
    email: EmailStr         # Validação Pydantic de formato de email
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    created_at: datetime
```

### Controller — Registro

**Arquivo:** `app/modules/auth/interface/router.py`

```python
@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    repo = SQLAlchemyUserRepository(db)
    hasher = BcryptPasswordHasher()
    use_case = RegisterUserUseCase(repo=repo, hasher=hasher)

    try:
        user = use_case.execute(email=body.email, password=body.password)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Email already registered")

    return UserResponse(
        id=user.id,
        email=user.email.address,
        is_active=user.is_active,
        created_at=user.created_at,
    )
```

### Controller — Login

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

### Mapeamento de exceções

| Exceção de domínio          | Código HTTP | Mensagem                      |
|-----------------------------|-------------|-------------------------------|
| `EmailAlreadyExistsError`   | 409         | "Email already registered"    |
| `InvalidCredentialsError`   | 401         | "Invalid email or password"   |

---

## Repositórios

### Padrão Repository neste Módulo

A interface `UserRepositoryPort` (port) é definida no domain. A implementação concreta
`SQLAlchemyUserRepository` (adapter) fica na infrastructure. O use case depende apenas
da interface (injeção via construtor), e o controller resolve a implementação concreta.

### Diagrama de Dependência

```
RegisterUserUseCase / LoginUseCase
  │  depende de (via construtor)
  ▼
UserRepositoryPort             ← interface no domain (port)
  ▲
  │  implementado por
SQLAlchemyUserRepository       ← classe na infrastructure (adapter)
  │  usa internamente
  ▼
SQLAlchemy Session             ← sessionmaker(engine)
  │  conecta a
  ▼
SQLite / PostgreSQL            ← banco de dados
```

### Métodos do Repositório

```python
class UserRepositoryPort(ABC):
    def save(self, user: User) -> User:
        """Persiste (insere ou atualiza) um usuário e retorna a versão persistida."""

    def find_by_email(self, email: str) -> User | None:
        """Busca um usuário pelo email. Retorna None se não encontrado."""

    def find_by_id(self, user_id: str) -> User | None:
        """Busca um usuário pelo ID (UUID como string). Retorna None se não encontrado."""
```

> 💡 `find_by_id` recebe `user_id: str` (não `uuid.UUID`) porque a API externa
> (controller) já trabalha com strings. A conversão para UUID ocorre dentro do
> repositório na reconstrução da entidade de domínio.

---

## Fluxos Principais

### Fluxo 1: Registro de Usuário

**Descrição:** Um novo usuário se cadastra fornecendo email e senha. O sistema valida o
email, hasheia a senha e persiste.

**Sequência:**

```
Cliente HTTP
  │
  │  POST /auth/register { "email": "user@ex.com", "password": "myPass123" }
  ▼
auth/interface/router.py::register()
  │  FastAPI valida body contra RegisterRequest (Pydantic EmailStr)
  │  FastAPI injeta db: Session via Depends(get_db)
  │  Controller instancia:
  │    repo = SQLAlchemyUserRepository(db)
  │    hasher = BcryptPasswordHasher()
  │    use_case = RegisterUserUseCase(repo, hasher)
  ▼
auth/application/use_cases.py::RegisterUserUseCase.execute()
  │  1. Verifica se email já existe:
  │     existing = repo.find_by_email("user@ex.com")
  │     → SQL: SELECT * FROM users WHERE email = ?
  │  2. Se existir → EmailAlreadyExistsError
  │  3. Hasheia senha:
  │     hashed = hasher.hash("myPass123")
  │     → bcrypt.hashpw + gensalt
  │  4. Cria User(email=EmailAddress(...), hashed_password=HashedPassword(...), is_active=True)
  │  5. Persiste:
  │     repo.save(user)
  │     → _to_orm() converte User → UserORM
  │     → session.merge(orm) executa UPSERT
  │     → session.commit()
  │     → _to_domain() reconverte UserORM → User
  ▼
HTTP 201 { "id": "uuid", "email": "user@ex.com", "is_active": true, "created_at": "..." }
```

**Regras de negócio aplicadas:**
- Email deve conter `@` (validado por `EmailAddress.__post_init__`)
- Email deve ser único no sistema (validado pelo use case)
- Senha é armazenada como hash bcrypt, nunca em plain text

**Erros possíveis e como são tratados:**
- `EmailAlreadyExistsError` → HTTP 409 Conflict
- `ValueError` (email inválido) → ⚠️ Não tratado explicitamente no controller — resultaria
  em HTTP 500. Seria adequado adicionar tratamento no controller ou middleware global.

### Fluxo 2: Login

**Descrição:** Um usuário registrado faz login com email e senha, recebendo um token JWT
para autenticar requisições subsequentes.

**Sequência:**

```
Cliente HTTP
  │
  │  POST /auth/login { "email": "user@ex.com", "password": "myPass123" }
  ▼
auth/interface/router.py::login()
  │  Controller instancia repo, hasher, token_provider, LoginUseCase
  ▼
auth/application/use_cases.py::LoginUseCase.execute()
  │  1. Busca usuário: user = repo.find_by_email("user@ex.com")
  │     → SQL: SELECT * FROM users WHERE email = ?
  │  2. Se None → InvalidCredentialsError
  │  3. Verifica senha: hasher.verify("myPass123", user.hashed_password.hash_passwd)
  │     → bcrypt.checkpw()
  │  4. Se False → InvalidCredentialsError
  │  5. Gera token: token_provider.generate({"sub": str(user.id)})
  │     → jwt.encode() com claims iat, exp
  │     → Retorna token JWT string
  ▼
HTTP 200 { "access_token": "eyJ...", "token_type": "bearer" }
```

**Regras de negócio aplicadas:**
- Para segurança, a mensagem de erro é genérica ("Invalid email or password") tanto para
  email inexistente quanto para senha incorreta, evitando enumeração de usuários.

**Erros possíveis e como são tratados:**
- `InvalidCredentialsError` → HTTP 401 Unauthorized

---

## Dependências entre Módulos

### Este módulo depende de:

| Módulo  | O que usa                           | Justificativa                              |
|---------|-------------------------------------|--------------------------------------------|
| shared  | `Base`                              | Classe base SQLAlchemy para `UserORM`      |
| shared  | `get_db()`                          | Injeção de sessão nos controllers          |
| shared  | `settings`                          | Configuração JWT usada no `PyJWTTokenProvider` |

### Outros módulos que dependem deste:

| Módulo       | O que consome deste módulo                                    |
|--------------|---------------------------------------------------------------|
| shared       | `PyJWTTokenProvider`, `InvalidTokenError`, `TokenExpiredError` (em `dependencies.py`) |
| todo         | Indiretamente via `get_current_user_id()` — o módulo todo usa o `user_id` extraído do JWT para autorização |

### Regra de Dependência

O módulo `auth` não depende de nenhum outro módulo de feature. A dependência de
`shared/dependencies.py` sobre `auth` é uma violação leve da regra (shared deveria ser
independente de módulos). O ideal seria que `get_current_user_id` fosse definido dentro
do módulo `auth` e exportado como uma dependência reutilizável.

---

[← Voltar ao Index](../index.md)
