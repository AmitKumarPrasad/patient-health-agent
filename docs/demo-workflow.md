# Demo workflow

This workflow uses synthetic data only.

## 1. Start the stack

```bash
docker compose up --build
```

Open the web application at `http://localhost:3000`.

## 2. Patient walkthrough

Sign in with the local Keycloak demo patient:

- Username: `demo.patient`
- Password: documented in `docs/demo-auth.md`

Then:

1. Open the dashboard.
2. Search for `General Medicine`.
3. Select `Demo Provider`.
4. Choose an available date and the `10:00` slot.
5. Book an appointment with a synthetic reason such as `Routine consultation`.
6. Confirm the appointment appears in My Appointments.
7. Cancel the appointment and verify the status changes to `cancelled`.

## 3. Provider walkthrough

Sign in as:

- Username: `demo.provider`
- Password: documented in `docs/demo-auth.md`

Verify that the provider sees only their assigned appointment and can transition it through the supported lifecycle.

## 4. Admin walkthrough

Sign in as:

- Username: `demo.admin`
- Password: documented in `docs/demo-auth.md`

Verify that the admin role can access appointments across patients/providers.

## 5. API smoke checks

The API exposes:

- `GET /health`
- `GET /health/db`
- `GET /api/providers`
- `GET /api/providers/{provider_id}/availability?requested_date=YYYY-MM-DD`
- `GET /api/appointments`
- `POST /api/appointments`
- `PATCH /api/appointments/{appointment_id}/status`
- `POST /api/agent/chat`

Every non-health endpoint requires a valid Keycloak bearer token, and appointment access is checked server-side.

## Test boundary

Do not use real patient, provider, or clinical information in this environment. The demo dataset is intentionally synthetic.
