FROM python:3.14.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv==0.8.22

COPY pyproject.toml uv.lock README.md ./
COPY FAIRS ./FAIRS

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["sh", "-c", "mkdir -p /app/FAIRS/resources/database /app/FAIRS/resources/checkpoints /app/FAIRS/resources/logs && .venv/bin/python -m uvicorn FAIRS.server.app:app --host 0.0.0.0 --port 8000"]
