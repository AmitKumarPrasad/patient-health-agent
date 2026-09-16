#!/usr/bin/env bash
set -euo pipefail

: "${API_BASE_URL:?API_BASE_URL must point to the recovered API}"

curl --fail --silent --show-error "${API_BASE_URL}/health/db" >/dev/null
curl --fail --silent --show-error "${API_BASE_URL}/ready" >/dev/null

echo "API database and readiness checks passed."
echo "Next verify recovered patient_documents/object checksums and run authenticated appointment, document-download, RAG, reminder, and audit smoke tests using a dedicated non-production recovery dataset."
