# Patient Health Agent API

FastAPI backend foundation for the Patient Health Agent platform.

## Local development

From the repository root:

```bash
docker compose up --build
```

Endpoints:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Database health: http://localhost:8000/health/db

For local Python development, create a virtual environment and install the project with your preferred Python package manager. The project targets Python 3.12 through 3.14.

## Design notes

- PostgreSQL access is isolated behind SQLAlchemy session dependencies.
- Configuration is loaded from environment variables and `.env`.
- The API layer must remain the enforcement point for authentication, authorization, validation, and business rules.
- Future LangGraph/MCP tools should call controlled service-layer operations rather than writing to PostgreSQL directly.
