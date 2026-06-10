# Glossário de Arquitetura

Este glossário define os termos arquiteturais utilizados na documentação do projeto,
contextualizando cada conceito com exemplos reais do código.

---

## Arquitetura Hexagonal (Ports & Adapters)

**Definição:** Padrão arquitetural proposto por Alistair Cockburn que organiza o código
em camadas concêntricas, com o domínio (regras de negócio) no centro, isolado de
detalhes externos. A comunicação com o mundo externo (banco de dados, APIs, UI) se dá
através de **ports** (interfaces/contratos definidos pelo domínio) e **adapters**
(implementações concretas dessas interfaces).

**Neste projeto:** O domínio (`app/modules/*/domain/`) é o centro. As interfaces
(`app/modules/*/domain/ports.py`) são ports. As implementações em
`app/modules/*/infrastructure/` e `app/modules/*/interface/` são adapters.

**Ver também:** [Arquitetura Hexagonal Aplicada](./arquitetura.md)

---

## Domínio (Domain)

**Definição:** A camada mais interna da arquitetura, contendo as entidades, value objects,
regras de negócio e interfaces (ports) que definem o que o sistema faz,
independentemente de como.

**Neste projeto:** Diretórios `app/modules/*/domain/`. Contém apenas código Python puro
(`dataclasses`, `ABC`) — zero imports de frameworks, ORM ou bibliotecas externas.

**Exemplos no código:**
- Entidade `User`: `app/modules/auth/domain/entities.py:8`
- Entidade `TodoList`: `app/modules/todo/domain/entities.py:38`
- Value Object `EmailAddress`: `app/modules/auth/domain/value_objects.py:4`

---

## Entidade (Entity)

**Definição:** Objeto de domínio com identidade própria (ID único) que persiste ao longo
do tempo, mesmo que seus atributos mudem. Diferente de value objects, duas entidades com
os mesmos atributos são distintas se tiverem IDs diferentes.

**Neste projeto:** Representadas como `@dataclass(kw_only=True)` com um campo `id:
uuid.UUID`. Contêm métodos de comportamento que encapsulam regras de negócio.

**Exemplos no código:**
- `User`: possui `id: uuid.UUID`, representa um usuário do sistema
  (`app/modules/auth/domain/entities.py:8`)
- `TodoList`: aggregate root, possui `id` e coleção de `TodoItem`
  (`app/modules/todo/domain/entities.py:38`)
- `TodoItem`: entidade filha dentro do agregado `TodoList`
  (`app/modules/todo/domain/entities.py:15`)

---

## Value Object

**Definição:** Objeto de domínio sem identidade própria, definido exclusivamente pelo
valor de seus atributos. É imutável — dois value objects com os mesmos valores são
considerados iguais. Geralmente contém validação no construtor.

**Neste projeto:** Implementados como `@dataclass(frozen=True)` com validação em
`__post_init__`.

**Exemplos no código:**
- `EmailAddress`: valida que o email contém `@` (`app/modules/auth/domain/value_objects.py:4`)
- `HashedPassword`: wrapper imutável para o hash bcrypt (`app/modules/auth/domain/value_objects.py:13`)
- `ListName`: valida que o nome não é vazio e não excede 100 caracteres
  (`app/modules/todo/domain/value_objects.py:4`)

---

## Agregado (Aggregate)

**Definição:** Cluster de entidades e value objects tratados como uma unidade coesa para
fins de persistência e consistência. Possui uma **raiz** (aggregate root) que é o único
ponto de acesso externo ao agregado. Todas as modificações nos objetos internos do
agregado devem passar pela raiz.

**Neste projeto:** `TodoList` é o aggregate root do agregado de tarefas. `TodoItem` é
uma entidade interna — nunca é acessada ou modificada diretamente de fora do agregado.
O repositório persiste o agregado inteiro de uma vez.

**Exemplos no código:**
- Aggregate root `TodoList`: `app/modules/todo/domain/entities.py:38`
- Métodos de acesso: `add_item()`, `complete_item()`, `rename_item()` — todos na raiz
- `verify_ownership()`: invariante do agregado aplicado na raiz

---

## Port

**Definição:** Interface (contrato) definida pelo domínio que especifica o que ele
precisa do mundo externo. O domínio depende apenas da interface, nunca da implementação
concreta (Inversão de Dependência). Ports podem ser de entrada (driving) ou de saída
(driven).

**Neste projeto:** Classes abstratas (ABC) em `app/modules/*/domain/ports.py`.

**Exemplos no código:**
- `UserRepositoryPort`: define `save()`, `find_by_email()`, `find_by_id()` (`app/modules/auth/domain/ports.py:6`)
- `PasswordHasher`: define `hash()`, `verify()` (`app/modules/auth/domain/ports.py:20`)
- `TokenProvider`: define `generate()`, `decode()` (`app/modules/auth/domain/ports.py:30`)
- `TodoListRepositoryPort`: define `save()`, `find_by_id()`, `find_all_by_owner()`, `delete()` (`app/modules/todo/domain/ports.py:8`)

---

## Adapter

**Definição:** Implementação concreta de um port. Conecta o domínio com uma tecnologia
específica (banco de dados, biblioteca de criptografia, framework HTTP). Adapters de
saída (driven) implementam ports do domínio; adapters de entrada (driving) usam ports
do domínio para expor funcionalidades.

**Neste projeto:**
- Adapters de saída: `app/modules/*/infrastructure/` (repositórios ORM, bcrypt, PyJWT)
- Adapters de entrada: `app/modules/*/interface/` (rotas FastAPI, schemas Pydantic)

**Exemplos no código:**
- `SQLAlchemyUserRepository`: adapter de saída (`app/modules/auth/infrastructure/repositories.py:11`)
- `BcryptPasswordHasher`: adapter de saída (`app/modules/auth/infrastructure/bcrypt_hasher.py:6`)
- `PyJWTTokenProvider`: adapter de saída (`app/modules/auth/infrastructure/jwt_provider.py:10`)
- `auth/router.py`: adapter de entrada — endpoints REST (`app/modules/auth/interface/router.py`)

---

## Use Case / Application Service

**Definição:** Classe ou função na camada de application que orquestra a execução de uma
operação de negócio. Recebe dependências via injeção, carrega entidades, chama métodos
de domínio e persiste resultados. Não contém regras de negócio — apenas coordena.

**Neste projeto:** Classes com um único método público `execute()` em
`app/modules/*/application/use_cases.py`.

**Exemplos no código:**
- `RegisterUserUseCase`: `app/modules/auth/application/use_cases.py:10`
- `LoginUseCase`: `app/modules/auth/application/use_cases.py:32`
- `CreateTodoListUseCase`: `app/modules/todo/application/use_cases.py:9`
- `AddTodoItemUseCase`: `app/modules/todo/application/use_cases.py:30`

---

## Repository

**Definição:** Padrão que abstrai o acesso a dados, oferecendo uma interface semelhante
a uma coleção em memória para o domínio. A interface (contrato) é definida no domínio;
a implementação concreta (com ORM, queries SQL) fica na infraestrutura.

**Neste projeto:** Interfaces em `domain/ports.py`, implementações em
`infrastructure/repositories.py`. O repositório mapeia entre entidades de domínio e
modelos ORM.

**Exemplos no código:**
- Interface: `TodoListRepositoryPort(ABC)` (`app/modules/todo/domain/ports.py:8`)
- Implementação: `SQLAlchemyTodoListRepository` (`app/modules/todo/infrastructure/repositories.py:11`)

**Ver também:** [Persistência e ORM](./orm.md#repositories--padrão-aplicado)

---

## Domain Service

**Definição:** Serviço no domínio que encapsula lógica de negócio que não pertence
naturalmente a uma única entidade ou value object. É stateless — opera sobre entidades,
value objects e ports, mas não mantém estado próprio.

**Neste projeto:** `AuthenticationService` coordena a autenticação combinando
repositório, hasher e token provider.

**Exemplo no código:**
- `AuthenticationService`: `app/modules/auth/domain/authentication_service.py:5`

> ⚠️ A lógica deste serviço está duplicada no `LoginUseCase`. O serviço de domínio não
> é utilizado pelos use cases atualmente.

---

## Domain Event

**Definição:** Representação de algo significativo que aconteceu no domínio. Entidades
disparam eventos que podem ser consumidos por outros componentes do sistema
(notificações, auditoria, sincronização). Parte do padrão de Event-Driven Architecture.

**Neste projeto:** ⚠️ **Não implementado.** Nenhuma entidade dispara eventos de domínio.
O projeto não possui event bus, handlers ou mecanismo de publicação/consumo de eventos.

---

## DTO (Data Transfer Object)

**Definição:** Objeto simples usado para transferir dados entre camadas ou entre sistemas,
sem comportamento ou lógica. Na arquitetura hexagonal, DTOs são usados nos adapters de
entrada (request/response) e, opcionalmente, entre application e interface.

**Neste projeto:**
- **DTOs de Interface (schemas Pydantic):** `RegisterRequest`, `LoginRequest`,
  `CreateListRequest`, `TodoListResponse`, etc. — definem o formato do JSON de
  entrada/saída da API REST.
- **DTOs de Application:** Não formalizados — os use cases recebem parâmetros primitivos
  e retornam entidades de domínio diretamente. A transformação para response DTO é feita
  no controller.

**Exemplos no código:**
- `RegisterRequest`: `app/modules/auth/interface/schemas.py:7`
- `TodoListResponse`: `app/modules/todo/interface/schemas.py:34`

---

## Injeção de Dependência (DI)

**Definição:** Técnica onde um componente recebe suas dependências do exterior (via
construtor, setter ou interface), em vez de instanciá-las internamente. Permite
desacoplamento e facilita testes com substituição de implementações.

**Neste projeto:** Constructor Injection manual (Pure DI), sem framework de IoC. Os use
cases recebem ports no construtor; os controllers instanciam as dependências manualmente.

**Exemplo no código:**
```python
# O use case declara dependência da interface (port)
class RegisterUserUseCase:
    def __init__(self, repo: UserRepositoryPort, hasher: PasswordHasher) -> None: ...

# O controller resolve com implementações concretas (adapters)
repo = SQLAlchemyUserRepository(db)
hasher = BcryptPasswordHasher()
use_case = RegisterUserUseCase(repo=repo, hasher=hasher)
```

**Ver também:** [Arquitetura — Injeção de Dependência](./arquitetura.md#injeção-de-dependência)

---

## Inversão de Dependência (DIP)

**Definição:** O "D" do SOLID. Estabelece que módulos de alto nível (domínio) não devem
depender de módulos de baixo nível (infraestrutura). Ambos devem depender de abstrações
(interfaces). As interfaces devem ser definidas pelo módulo de alto nível.

**Neste projeto:** O domínio define `UserRepositoryPort` (abstração). A infraestrutura
implementa `SQLAlchemyUserRepository`. O domínio não sabe que SQLAlchemy existe. A seta
de dependência vai da infraestrutura para o domínio, nunca o contrário.

---

## Monolito Modular

**Definição:** Aplicação que roda como um único processo/deploy, mas cujo código é
organizado em módulos com fronteiras bem definidas e acoplamento controlado. Oferece o
equilíbrio entre a simplicidade operacional de um monolito e a organização de
microserviços.

**Neste projeto:** FastAPI app único (`app/main.py`), mas código organizado em módulos
independentes (`modules/auth/`, `modules/todo/`) com suas próprias camadas (domain,
application, infrastructure, interface). Comunicação entre módulos via `shared/` e
dependências FastAPI.

**Ver também:** [Arquitetura — Monolito Modular](./arquitetura.md#organização-dos-módulos-monolito-modular)

---

## ORM (Object-Relational Mapper)

**Definição:** Técnica/ferramenta que mapeia objetos de uma linguagem de programação para
tabelas de um banco de dados relacional, permitindo operações CRUD sem SQL explícito.

**Neste projeto:** **SQLAlchemy 2.x** com estilo `DeclarativeBase` e anotações
`Mapped`/`mapped_column`. Os modelos ORM (`*ORM`) são separados das entidades de domínio,
com mapeamento explícito feito nos repositórios.

**Ver também:** [Persistência e ORM](./orm.md)

---

## Persistence Model vs Domain Model

**Definição:** Distinção entre o modelo usado para persistir dados (com anotações de ORM,
relacionamentos, constraints de banco) e o modelo de domínio (com regras de negócio,
value objects, métodos de comportamento). Mantê-los separados é um dos pilares da
Arquitetura Hexagonal e do DDD tático.

**Neste projeto:** Separação total. Exemplo:
- `User` (domain model): `app/modules/auth/domain/entities.py` — `@dataclass` puro
- `UserORM` (persistence model): `app/modules/auth/infrastructure/orm_models.py` — herda de `Base`
- Mapeamento bidirecional: `_to_orm()` e `_to_domain()` no repositório

**Ver também:** [ORM — Estratégia de Mapeamento](./orm.md#estratégia-de-mapeamento-entidades-orm-vs-entidades-de-domínio)

---

## Unit of Work

**Definição:** Padrão que gerencia transações e coordena a persistência de múltiplos
objetos como uma unidade atômica. Mantém controle de quais objetos foram modificados
e faz flush/commit no momento certo.

**Neste projeto:** ⚠️ **Não implementado explicitamente.** Cada método do repositório
faz seu próprio `session.commit()`. Para operações que precisam de atomicidade entre
múltiplos repositórios, não há mecanismo. A sessão do SQLAlchemy (`Session`) oferece o
comportamento transacional subjacente, mas não há uma abstração Unit of Work.

**Ver também:** [ORM — Transações](./orm.md#transações)

---

[← Voltar ao Index](./index.md)
