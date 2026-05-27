FROM python:3.14-slim-trixie AS builder

WORKDIR /app

  #COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.14-slim-trixie

ENV PATH=/root/.local/bin:$PATH
WORKDIR /app

COPY --from=builder /root/.local /root/.local

COPY . .

USER 1000

CMD ["python", "test.py"]