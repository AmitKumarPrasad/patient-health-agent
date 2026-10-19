# Deployment and operational runbook

## Local demo

1. Copy `.env.example` to `.env`.
2. Set `OPENAI_API_KEY` for AI and embedding features. Set `TAVILY_API_KEY` only when public web research is needed.
3. Start the stack:

```bash
docker compose up --build
```

4. Open the web app at `http://localhost:3000`.
5. Keycloak is available at `http://localhost:8080` and the local realm is imported automatically.
6. Mailpit is available at `http://localhost:8025`.
7. MinIO console is available at `http://localhost:9001`.

## Database

The API entrypoint runs Alembic migrations. For an existing deployment that receives Step 19 document changes, run the reindex worker once:

```bash
docker compose run --rm api python -m app.workers.reindex_documents
```

## Production requirements

- Replace all development passwords and MinIO credentials.
- Terminate TLS at a reverse proxy and use HTTPS for the web application and Keycloak.
- Set `CORS_ORIGINS` to the exact production web origin(s).
- Provide a production SMTP service instead of Mailpit.
- Keep the MinIO bucket private and use a dedicated service account with least-privilege access.
- Store OpenAI and Tavily API keys in a secret manager; never commit them.
- Use synthetic/demo data for demonstrations. Do not upload real patient data into this repository's demo environment.
- Review provider access policies with the clinic's legal/privacy requirements before enabling production clinical use.

## Security boundary

The application resolves patient/provider identity from Keycloak and applies authorization in the backend services. AI agents are not granted direct database credentials or unrestricted object-storage access. Clinical record access by providers is limited to patients with an active or completed appointment relationship and produces an audit event.

AI features are workflow and information-retrieval aids. They are not diagnostic or treatment-decision systems.


## Deployment smoke check

After deploying the API, run the no-credentials health/readiness probe:

```bash
python3 ops/smoke/check_deployment.py https://api.example.com
```

For a developer-only loopback instance (never for a public HTTP endpoint):

```bash
python3 ops/smoke/check_deployment.py http://localhost:8000 --allow-local-http
```

The probe checks `/health` and `/ready`, requires HTTP 200 with JSON statuses
`ok` and `ready`, and exits nonzero on failure. It does **not** validate
authentication, Keycloak, document storage, patient workflows or AI output.
Complete these separately with synthetic test accounts before handling real patient data.
