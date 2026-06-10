FROM python:3.14-slim AS builder

WORKDIR /app

COPY pyproject.toml .

RUN pip install --no-cache-dir --user . \
 && pip install --no-cache-dir --user "uvicorn[standard]" psycopg2-binary

FROM python:3.14-slim

ENV PATH=/root/.local/bin:$PATH \
    DATABASE_URL=sqlite:///./todo_app.db

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY app/ .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
