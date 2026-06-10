# overengineered-todolist
An overengineered todo list


 # Development Guide

## Docker Compose (recommended)
```bash
cp .env.example .env
docker compose up -d --build
```
A API fica em `http://localhost:8000`. PostgreSQL na porta `5432`.

### Resetar o banco
```bash
docker compose down -v && docker compose up -d --build
```

## Local (venv)
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
alembic upgrade head
uvicorn main:app --reload
```
Usa SQLite por padrão (definido em `.env`).

# Git Guidelines
### Commit Messages:
https://www.conventionalcommits.org/en/v1.0.0/#examples

### Code Submitions and Pull Requests
https://trunkbaseddevelopment.com/

