# AI Health-Record Navigation

Step 19 upgrades the Step 18 assistant to retrieval-augmented generation (RAG).

## Pipeline

1. Patient uploads a PDF or text document.
2. The backend keeps the original object in private MinIO storage.
3. PDF/text content is extracted server-side.
4. Text is normalized and split into overlapping chunks.
5. Chunks are stored with the owning patient and source document.
6. When `OPENAI_API_KEY` is configured, chunks and queries use the configured OpenAI embedding model.
7. Retrieval is always filtered by the authenticated patient before content reaches the LLM.
8. The record agent answers from the retrieved context only.

The database stores embeddings as JSON for the demo so PostgreSQL does not require a vector extension. This is suitable for the demo scale; a production deployment should move retrieval to a native vector index such as pgvector.

## API

- `POST /api/records/assistant`
- `GET /api/records/search?q=...`
- `GET /api/records/{document_id}/text`

All endpoints require the `patient` Keycloak role. The backend resolves the authenticated Keycloak subject to the patient record before document access or retrieval.

## Supported AI extraction

- `application/pdf`: text extraction with `pypdf`.
- `text/plain`: direct UTF-8 extraction.
- JPEG/PNG: stored and downloadable, but not OCR-indexed in this step.

## Safety boundary

The assistant is a workflow and record-navigation aid. It must not diagnose, recommend treatment, interpret clinical findings as medical advice, or invent facts. Clinical questions should be directed to a qualified clinician.

The demo environment must contain synthetic data only.
