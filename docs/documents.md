# Patient documents

Step 17 adds private patient document storage using PostgreSQL for metadata and MinIO for object bytes.

## API

- `GET /api/documents` — list the authenticated patient's documents.
- `POST /api/documents` — upload a document as multipart form data.
- `GET /api/documents/{document_id}` — download a document after ownership validation.
- `DELETE /api/documents/{document_id}` — delete a document after ownership validation.

## Supported demo types

- PDF
- JPEG
- PNG
- Plain text

Maximum size is 10 MB per document.

## Storage model

```text
Keycloak JWT
    ↓
FastAPI patient identity
    ↓
PostgreSQL metadata
    ↓
MinIO private object: patients/<patient-id>/<object-id>/<safe-filename>
```

The API does not expose MinIO credentials or public object URLs to the browser.

## Local storage

MinIO is available from Compose on ports `9000` (API) and `9001` (console). The demo bucket is `patient-records`.

Do not upload real patient or clinical information to the local demo environment.
