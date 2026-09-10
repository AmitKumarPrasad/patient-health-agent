# Patient Health Agent

An open-source, self-hosted healthcare appointment and patient engagement platform for client demos and incremental production development.

## Demo goals

- Patient and provider appointment management
- AI-assisted appointment discovery and booking
- Automated appointment reminders
- Secure digital health-record document storage
- Video consultation integration
- Role-based access control
- Architecture designed for future paid-provider integrations

## Technology

- Next.js + TypeScript
- FastAPI + Python
- PostgreSQL
- LangGraph
- Keycloak
- MinIO
- Jitsi Meet
- Mailpit
- Docker Compose
- MCP
- OpenAI + Tavily for the configured AI workflow

## Repository structure

```text
apps/
  web/          # Next.js patient UI
  api/          # FastAPI backend and LangGraph orchestration
  agent/        # agent workflow components
  mcp-server/   # MCP tools backed by the validated application service layer
docs/           # Architecture and product documentation
```

## Current workflow

The current web application, API, LangGraph workflow, and MCP server provide:

1. Keycloak browser authentication using Authorization Code + PKCE.
2. Patient profile loading from the authenticated Keycloak subject.
3. Provider search by specialty and availability lookup by date.
4. Appointment booking, listing and patient cancellation.
5. Provider appointment and availability management.
6. AI appointment assistant chat and assisted booking workflow.
7. Secure patient health-record upload, search, download and deletion.
8. Authorized provider access to patient records.
9. Video consultation launch for eligible appointments.
10. Scheduled appointment reminders with an admin operation to process due notifications.
11. Admin audit-log search with filtering, pagination, and CSV export.
12. API health and database readiness endpoints for operational checks.
13. MCP tools for provider discovery, availability lookup, authenticated patient-record search, and appointment booking.

The frontend talks only to FastAPI; it never connects directly to PostgreSQL or the AI provider. The LangGraph agent and MCP server both delegate business operations to the same validated service layer rather than duplicating scheduling or record-access rules.

## Operational endpoints

- `GET /health` — basic API liveness check.
- `GET /health/db` — database connectivity check.
- `GET /ready` — readiness check that returns HTTP 503 when the database is unavailable.
- `GET /api/admin/audit` — admin-only audit event search.
- `GET /api/admin/audit/export` — admin-only filtered audit CSV export.
- `POST /api/admin/notifications/process` — admin-only processing of due notifications.

## MCP server

The MCP server is a separate Docker service and runs over stdio for trusted agent/client integration. Its tools are deliberately narrow and delegate to the existing application service layer:

- `find_providers(specialty)`
- `available_slots(provider_id, requested_date)`
- `patient_records(subject, query)`
- `book_slot(subject, provider_id, starts_at, ends_at, reason)`

Patient identity is represented by the authenticated Keycloak subject at the tool boundary; the MCP layer does not authorize requests using a caller-supplied patient database ID.

## Run locally

Create your local environment from `.env.example` and configure Keycloak with a `patient-health-web` public client using the appropriate redirect/web origins for `http://localhost:3000`.

Then run:

```bash
docker compose up --build
```

Open `http://localhost:3000` for the web application and `http://localhost:8000/docs` for the FastAPI API documentation.

## Important safety boundary

This repository is for development/demo purposes. Do not use real patient or clinical data in the demo environment. Clinical decision-making is outside the scope of the AI assistant; the agent is intended to assist with workflows such as finding availability, scheduling, reminders and record navigation.

## Dependency reproducibility

The frontend dependency graph is committed in `apps/web/package-lock.json`, and CI uses `npm ci` so dependency resolution is reproducible from the lockfile.
