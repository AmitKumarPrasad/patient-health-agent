FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.116,<1.0" \
    "uvicorn[standard]>=0.35,<1.0" \
    "sqlalchemy>=2.0,<3.0" \
    "psycopg[binary]>=3.2,<4.0" \
    "alembic>=1.16,<2.0" \
    "pydantic-settings>=2.10,<3.0" \
    "python-jose[cryptography]>=3.5,<4.0" \
    "httpx>=0.28,<1.0" \
    "langgraph>=1.2,<2.0" \
    "langchain-openai>=1.0,<2.0" \
    "langchain-tavily>=0.2,<1.0" \
    "langchain-core>=1.0,<2.0" \
    "minio>=7.2,<8.0" \
    "python-multipart>=0.0.20,<1.0" \
    "pypdf>=5.0,<7.0"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
