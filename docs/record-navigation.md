# AI Health-Record Navigation

Step 18 adds a patient-scoped record navigation assistant.

## Capabilities

- Search the authenticated patient's document metadata.
- Read `text/plain` documents through an authorized backend tool.
- Summarize returned record information with the configured OpenAI model.

## API

- `POST /api/records/assistant`
- `GET /api/records/search?q=...`
- `GET /api/records/{document_id}/text`

All endpoints require the `patient` Keycloak role. The backend resolves the authenticated Keycloak subject to the patient record before accessing documents.

## Safety boundary

The assistant is a workflow and record-navigation aid. It must not diagnose, recommend treatment, interpret clinical findings as medical advice, or invent facts. Clinical questions should be directed to a qualified clinician.

The demo environment must contain synthetic data only.
