# Demo authentication

Step 13 bootstraps Keycloak with a local `patient-health` realm.

## Roles

- `patient`: patient portal and patient-owned appointment actions
- `provider`: provider portal, availability management, and assigned appointment actions
- `admin`: administrative appointment access

## Demo users

| Username | Role | Password |
|---|---|---|
| `demo.patient` | `patient` | `ChangeMe!Patient123` |
| `demo.provider` | `provider` | `ChangeMe!Provider123` |
| `demo.admin` | `admin` | `ChangeMe!Admin123` |

These credentials are for local/demo use only. Replace them before any shared or deployed environment.

## Start

```bash
docker compose up --build
```

The API container applies Alembic migrations automatically, including the demo identity seed. Keycloak imports the realm configuration on startup when the realm does not already exist.

Open the application at `http://localhost:3000` and the Keycloak administration console at `http://localhost:8080`.

## Identity mapping

The demo Keycloak user IDs are deterministic UUIDs and match the `external_id` values seeded into PostgreSQL. This makes the JWT `sub` claim resolve to the correct application user without storing credentials in PostgreSQL.
