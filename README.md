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
- OpenAI + Tavily for the configured AI workflow

## Repository structure

```text
apps/
  web/          # Next.js patient UI
  api/          # FastAPI backend
  agent/        # LangGraph agent workflows (planned expansion)
  mcp-server/   # MCP tools exposed to agents (planned)
docs/           # Architecture and product documentation
```

## Current workflow

The Step 12 web application provides:

1. Keycloak browser authentication using Authorization Code + PKCE.
2. Patient profile loading from the authenticated Keycloak subject.
3. Provider search by specialty.
4. Provider availability lookup by date.
5. Appointment booking.
6. Appointment listing and patient cancellation.
7. AI appointment assistant chat.

The frontend talks only to FastAPI; it never connects directly to PostgreSQL or the AI provider.

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

The frontend dependencies are pinned by `apps/web/package-lock.json`, and CI installs them with `npm ci`.
