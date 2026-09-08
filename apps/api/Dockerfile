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
    "pydantic-settings>=2.10,<3.0"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
