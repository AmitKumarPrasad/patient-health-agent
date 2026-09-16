# Backup & Disaster Recovery

This runbook defines the minimum backup/restore controls for the Patient Health Agent demo/production-development architecture. The repository must not be used with real patient data in the demo environment.

## Recovery objectives

- **PostgreSQL RPO:** 15 minutes when continuous WAL archiving is enabled; otherwise the RPO equals the backup interval.
- **PostgreSQL RTO:** target 60 minutes.
- **MinIO document RPO:** 15 minutes or the replication interval configured by the storage platform.
- **MinIO document RTO:** target 60 minutes for a restore of the required bucket.

RPO/RTO are operational targets, not guarantees. Validate them against the actual storage, network, and managed-service capabilities before production use.

## What must be backed up

1. PostgreSQL database, including schema and application data.
2. PostgreSQL WAL when point-in-time recovery is required.
3. MinIO `patient-records` objects and their metadata.
4. Keycloak realm configuration and production identity-provider configuration (never export secrets into Git).
5. Deployment configuration and secret references. Do not place credentials in backups committed to the repository.

## PostgreSQL logical backup

Run from a trusted backup host with network access to PostgreSQL:

```bash
mkdir -p backups/postgres
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > "backups/postgres/patient_health_$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Restore into an empty recovery database:

```bash
createdb patient_health_recovery
pg_restore --clean --if-exists --no-owner --no-acl \
  --dbname=patient_health_recovery \
  backups/postgres/<backup>.dump
```

Run Alembic migrations after restore if the recovered database is behind the application revision:

```bash
alembic upgrade head
```

Never restore production data into the demo environment.

## PostgreSQL point-in-time recovery

For production, use PostgreSQL physical backups plus WAL archiving to independent storage. Retain a base backup and WAL segments long enough to satisfy the approved retention policy. A PITR test must verify recovery to a timestamp before the incident and application connectivity afterward.

Logical `pg_dump` alone does **not** provide point-in-time recovery.

## MinIO backup

Use object replication or a scheduled off-host copy to independent storage. A backup is only considered valid after objects can be listed and representative objects can be downloaded and checksum-verified.

Example using the MinIO Client (`mc`) against a configured backup target:

```bash
mc mirror --overwrite minio/patient-records backup/patient-records
```

For production, the destination should be isolated from the primary MinIO failure domain and protected with encryption, access controls, and retention/immutability appropriate to the organization's data policy.

## Restore verification

After restoring PostgreSQL and object storage:

1. Run `alembic upgrade head`.
2. Verify `/health/db` and `/ready`.
3. Verify patient-document rows exist for the recovery dataset.
4. Verify every sampled document object exists in the restored bucket.
5. Compare SHA-256 values against `patient_documents.sha256`.
6. Verify document download and RAG retrieval for a test patient.
7. Verify appointment creation/listing and reminder processing.
8. Review audit events generated during the recovery validation.

## Retention

A production policy should define at minimum:

- daily backups retained for 35 days;
- weekly backups retained for 12 weeks;
- monthly backups retained for 12 months where required by policy;
- WAL retained long enough to cover the PITR window;
- encrypted off-host copies;
- periodic restore tests, at least quarterly.

The exact retention period must be approved by the data owner/legal/compliance team rather than inferred from this repository.

## Backup security

- Encrypt backups in transit and at rest.
- Store backup credentials outside Git.
- Restrict restore permissions to authorized operators.
- Keep backup storage in a separate failure/security domain.
- Do not include `.env`, API keys, database passwords, or Keycloak client secrets in backup artifacts stored in the repository.
- Treat database and document backups as sensitive data with the same or stronger access controls as the primary systems.

## Incident sequence

**Declare -> isolate -> identify recovery point -> restore PostgreSQL -> restore MinIO -> verify checksums -> run migrations -> health-check -> functional test -> review audit logs -> resume traffic.**

Document the recovered timestamp, backup identifiers, validation results, data loss window, and any follow-up corrective actions.