# Parallel Development Board

The repository is organized for **three independently executed coding workstreams**. GitHub branches and issues coordinate work; they do **not** run autonomous developers.

| Workstream | Stable branch | Primary paths | First milestone |
| --- | --- | --- | --- |
| Backend | `workstream/backend` | `apps/api/`, migrations | API reliability, permissions, production readiness |
| Frontend | `workstream/frontend` | `apps/web/` | Responsive UX, error states, accessibility |
| AI / QA | `workstream/ai-qa` | LangGraph/MCP, API tests, Playwright | Research quality, security tests, full E2E |

Each workstream should open a short-lived feature branch from current `main` and use a pull request. Cross-cutting API contract changes are coordinated before implementation.

## Launch gate
- All six CI checks green.
- No unresolved high/critical security findings.
- E2E patient, provider, and admin flows with synthetic data.
- Deployed environment smoke checks, monitoring, backups and restore drill.
- Privacy/clinical risk review completed before actual patient data.

## Administrative follow-up
Configure GitHub branch protection or repository rulesets for `main` (PR required, review required, all six required checks, block force pushes). The connected GitHub integration does not provide a branch-protection write capability, so this step must be completed by an authorized repository administrator.
