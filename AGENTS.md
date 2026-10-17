# Parallel agent collaboration (Patient Health Agent)

Three independent coding sessions or developers may work concurrently, **one branch per workstream**. Branches alone do not launch autonomous agents.

## Workstreams
- `workstream/backend`: `apps/api/`, database migrations, API auth, backend tests; own backend API contracts.
- `workstream/frontend`: `apps/web/`, UX, accessibility, frontend integration tests; consume stable API contracts.
- `workstream/ai-qa`: research agent, RAG, MCP, security and end-to-end QA, primarily `apps/agent/`, `apps/mcp-server/`, `apps/api/app/agents/`, `apps/api/tests/`, `apps/web/e2e/`.

## Rules
1. Start feature branches from the latest `main` (e.g. `backend/<issue>-topic`, `frontend/<issue>-topic`, `ai-qa/<issue>-topic`). Do not work directly on the workstream branches. The three `workstream/*` branches are stable starting points, not shared integration branches.
2. Each agent works only on its assigned issue; coordinate changes to shared files like `apps/web/lib/api.ts`, `apps/api/app/api/`, `docker-compose.yml`, `package-lock.json` and `.github/workflows/ci.yml` before editing.
3. Keep synthetic test data only; never send patient data, access tokens, or secrets to AI tools, issues or CI logs.
4. Require focused unit/integration tests and the existing six CI jobs (api, web, mcp, compose, backup, e2e); fix RED before merging.
5. Open one PR into `main` per issue, include reproduction/verification steps and any API contract changes. Do not force push to `main`.
6. Security-sensitive changes (auth, patient records, authorization, retention, production infrastructure) require independent review. Do not claim clinical/production readiness based solely on CI.
7. Prefer small, reviewable PRs; merge only after required checks and reviews. The repo administrator should configure GitHub branch protection/rulesets to enforce this.

## Integration order
1. Backend contract or migration PR (when required).
2. Frontend integration PR against the merged contract.
3. AI/QA tests/security PR; use mocks or feature flags to avoid cross-branch dependency.
All three can progress in parallel on independent issues. Rebase each feature branch on the latest `main` before merge.
