# Admin Operations Runbook

## Scope

The admin UI at `/admin/audit` provides a restricted operational view for security-relevant activity and a manual control for processing due notifications.

## Audit log

Use the audit log to review activity across patients, providers, appointments, documents, and notification processing.

Available filters:

- `action` — narrow to a specific audit action such as `appointment.booked` or `notification.process`.
- `actor_subject` — filter by the authenticated subject that performed the operation.
- `patient_id` — focus the review on one patient.
- `outcome` — show successful or failed operations.

The table is newest-first and supports pagination so the operator can review more than the first 100 events without changing the active filters.

## Process due notifications

The **Process due notifications** control calls the protected admin endpoint:

```text
POST /api/admin/notifications/process
```

The operation processes currently due notifications using the existing notification service and creates an `notification.process` audit event with the processed count.

After processing, the audit table is refreshed so the resulting administrative event is visible immediately.

## Service checks

Use the operational endpoints when validating a local or demo deployment:

```text
GET /health
GET /health/db
GET /ready
```

`/health` verifies the API process is responding. `/health/db` checks database connectivity. `/ready` returns HTTP 503 when the database cannot be reached, making it suitable for readiness checks.

## Security expectations

Admin access is role-protected by the application authentication layer. Do not place real patient or clinical data into the demo environment. Production deployments still require formal privacy/compliance review, secret management, backup/recovery, retention controls, and environment-specific security configuration.
