#!/usr/bin/env bash
set -euo pipefail

: "${SOURCE_ALIAS:?SOURCE_ALIAS must name the configured primary MinIO alias}"
: "${DEST_ALIAS:?DEST_ALIAS must name the configured backup MinIO alias}"
BUCKET="${MINIO_BUCKET:-patient-records}"

mc mirror --overwrite "${SOURCE_ALIAS}/${BUCKET}" "${DEST_ALIAS}/${BUCKET}"

echo "Mirrored MinIO bucket: ${BUCKET}"
