# Overengineered Todolist — Documentação Técnica

## Visão Geral

O **Overengineered Todolist** é uma aplicação de lista de tarefas (todo list) construída com
propósito educacional, demonstrando a aplicação prática de Arquitetura Hexagonal (Ports &
Adapters) e Domain-Driven Design (DDD) em um monolito modular. O sistema permite que usuários
se registrem, façam login via JWT e gerenciem múltiplas listas de tarefas com itens que podem
ser concluídos, reabertos e renomeados.

### Stack Tecnológica

| Categoria               | Tecnologia                          | Versão            |
|--------------------------|-------------------------------------|-------------------|
| Linguagem                | Python                              | >= 3.10 (3.14)    |
| Framework Web            | FastAPI                             | (latest)          |
| Validação / Config       | Pydantic + Pydantic-Settings        | (latest)          |
| ORM                      | SQLAlchemy 2.x (DeclarativeBase)    | (latest)          |
| Migrations               | Alembic                             | (latest)          |
| Autenticação (hash)      | bcrypt                              | (latest)          |
| Autenticação (token)     | PyJWT                               | (latest)          |
| Servidor HTTP            | Uvicorn                             | (latest)          |
| Banco de Dados (dev)     | SQLite                              | —                 |
| Banco de Dados (prod)    | PostgreSQL 16                       | via Docker Compose|
| Build System             | setuptools                          | >= 68             |
| Gerenciamento de Depend. | pip + pyproject.toml                | —                 |
| Testes                   | pytest + httpx                      | (latest)          |
| Linting / Formatação     | black + isort                       | (latest)          |
| Containerização          | Docker (multi-stage) + Docker Compose| —                |
| CI/CD                    | GitHub Actions                      | —                 |

### Estrutura de Módulos

O projeto é organizado como um **monolito modular** com dois bounded contexts (módulos de
negócio) e um pacote `shared` para concerns transversais:

| Módulo  | Responsabilidade                            | Documentação                     |
|---------|---------------------------------------------|----------------------------------|
| auth    | Registro, login e autenticação de usuários  | [auth.md](./modulos/auth.md)     |
| todo    | Gerenciamento de listas de tarefas e itens  | [todo.md](./modulos/todo.md)     |
| shared  | Configuração, banco de dados, DI e exceções | (documentado no index e orm.md)  |

## Navegação Rápida

- [Arquitetura Hexagonal Aplicada](./arquitetura.md) — Explicação detalhada de cada camada e como o projeto as implementa
- [Persistência e ORM](./orm.md) — Documentação do SQLAlchemy, entidades, mapeamento e repositórios
- [Módulo Auth](./modulos/auth.md) — Registro, login, JWT, bcrypt
- [Módulo Todo](./modulos/todo.md) — Aggregate TodoList, use cases, repository
- [Glossário](./glossario.md) — Definições dos termos arquiteturais usados

## Como Rodar o Projeto

### Pré-requisitos

- Python >= 3.10
- pip (gerenciador de pacotes)

### Ambiente de Desenvolvimento

```bash
# Criar e ativar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate      # Linux/MacOS

# Instalar dependências (produção + dev)
pip install -e ".[dev]"

# Copiar e preencher variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# Executar migrations
cd app
alembic upgrade head

# Rodar o servidor
uvicorn app.main:app --reload

# Rodar os testes
pytest app/tests/ -v
```

### Via Docker

```bash
# Subir banco PostgreSQL
docker compose up -d

# Ajustar DATABASE_URL no .env para:
# DATABASE_URL=postgresql://user:password@localhost:5432/todolist
```

### CI/CD

O pipeline de CI (GitHub Actions) em `.github/workflows/code-lint.yaml` executa:
1. Linting com `black --check .` e `isort --check .`
2. Testes com `pytest app/tests/ -v`

---

[← Voltar ao topo](#overengineered-todolist--documentação-técnica)
