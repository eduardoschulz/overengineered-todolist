# overengineered-todolist
Uma lista de tarefas exageradamente engenheirada.

[📊 Relatório de cobertura de testes](coverage.txt)

# Guia de Desenvolvimento

## Docker Compose (recomendado)
```bash
cp .env.example .env
docker compose up -d --build
```
A API fica em `http://localhost:8000`. PostgreSQL na porta `5432`.

Imagem disponível no GitHub Packages:
```bash
docker pull ghcr.io/eduardoschulz/overengineered-todolist:latest
```

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

# Guia de Git
### Mensagens de Commit:
https://www.conventionalcommits.org/en/v1.0.0/#examples

### Envio de Código e Pull Requests
https://trunkbaseddevelopment.com/
