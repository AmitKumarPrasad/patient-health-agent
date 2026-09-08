FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/api

WORKDIR /app
COPY apps/mcp-server/pyproject.toml /app/mcp/pyproject.toml
RUN pip install --no-cache-dir "mcp>=1.9,<2.0" \
    "fastapi>=0.116,<1.0" "sqlalchemy>=2.0,<3.0" "psycopg[binary]>=3.2,<4.0" \
    "minio>=7.2,<8.0" "pydantic-settings>=2.10,<3.0"
COPY apps/api /app/api
COPY apps/mcp-server/server.py /app/mcp/server.py
WORKDIR /app/mcp
CMD ["python", "server.py"]
