#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/patient_health_${STAMP}.dump"

pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > "$OUT"

echo "Created PostgreSQL backup: $OUT"
