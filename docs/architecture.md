# Architecture

## System overview

The platform is split into independently deployable application boundaries:

1. **Web** — patient, doctor and admin experiences.
2. **API** — authentication-aware REST API and business services.
3. **Agent** — LangGraph orchestration for workflow assistance.
4. **MCP server** — explicit tools the agent can invoke.
5. **PostgreSQL** — transactional application data.
6. **MinIO** — local object storage for demo documents.
7. **Keycloak** — identity and role management.
8. **Ollama** — local model serving.
9. **Jitsi** — video consultation.
10. **Mailpit** — local email capture for reminders.

## Core principle

AI does not directly mutate the database. The agent calls narrowly scoped application/MCP tools, and those tools enforce authorization and business validation before performing writes.

```text
Browser
  |
  v
Next.js Web
  |
  v
FastAPI API ------------------> PostgreSQL
  |                                  |
  |                                  +--> MinIO
  |
  +--> LangGraph Agent
          |
          +--> MCP Tools ----------> FastAPI service layer
          |
          +--> Ollama

Notifications --> Mailpit
Consultations --> Jitsi
Identity -------> Keycloak
```

## Initial workflow

The first vertical slice will be:

`Patient request -> Agent -> availability tool -> booking confirmation -> appointment persisted -> reminder event`

The implementation will add clinical features only after the workflow foundation is stable, and the AI layer will not be positioned as a diagnostic or treatment decision-maker.
