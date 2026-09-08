# Patient Health Agent

An open-source, self-hosted healthcare appointment and patient engagement platform for client demos and incremental production development.

## Demo goals

- Patient and doctor appointment management
- AI-assisted appointment discovery and booking
- Automated appointment reminders
- Secure digital health-record document storage
- Video consultation integration
- Role-based access control
- Architecture designed for future paid-provider integrations

## Demo-first technology strategy

The initial version is designed to run locally with open-source/self-hosted components:

- Next.js + TypeScript
- FastAPI + Python
- PostgreSQL
- LangGraph
- MCP
- Ollama + a local open-weight model
- Keycloak
- MinIO
- Jitsi Meet
- Mailpit
- Docker Compose

Paid providers can be introduced later through provider interfaces without rewriting core business logic.

## Repository structure

```text
apps/
  web/          # Next.js patient, doctor and admin UI
  api/          # FastAPI backend
  agent/        # LangGraph agent workflows
  mcp-server/   # MCP tools exposed to agents
packages/       # Shared contracts and UI primitives
infrastructure/ # Local infrastructure configuration
docs/           # Architecture, security and product documentation
```

## Important safety boundary

This repository is for development/demo purposes. Do not use real patient or clinical data in the demo environment. Clinical decision-making is outside the scope of the AI assistant; the agent is intended to assist with workflows such as finding availability, scheduling, reminders and record navigation.

## Development status

Phase 1: repository foundation and architecture.
