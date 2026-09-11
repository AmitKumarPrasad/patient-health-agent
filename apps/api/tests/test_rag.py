from __future__ import annotations

from uuid import uuid4

from app.models.document_chunk import PatientDocumentChunk
from app.services import rag


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return _FakeResult(self.rows)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


def _patient():
    from app.models.patient import Patient

    return Patient(id=uuid4(), external_id="patient-1")


def test_semantic_retrieval_is_patient_scoped(monkeypatch):
    patient = _patient()
    chunk = PatientDocumentChunk(
        id=uuid4(),
        document_id=uuid4(),
        patient_id=patient.id,
        chunk_index=2,
        content="Blood pressure follow-up plan",
        embedding=[0.1] * 1536,
    )
    db = _FakeDB([(chunk, "visit-note.txt", 0.12)])
    monkeypatch.setattr(rag, "_embed_query", lambda _: [0.2] * 1536)

    results = rag.retrieve_patient_chunks(db, patient, "blood pressure")

    assert results[0]["document_name"] == "visit-note.txt"
    assert results[0]["chunk_index"] == 2
    assert results[0]["score"] == 0.88
    assert str(patient.id) in str(db.statement.compile(compile_kwargs={"literal_binds": True}))


def test_lexical_fallback_returns_citation_metadata(monkeypatch):
    patient = _patient()
    chunk = PatientDocumentChunk(
        id=uuid4(),
        document_id=uuid4(),
        patient_id=patient.id,
        chunk_index=0,
        content="Medication review and blood pressure follow-up",
    )
    db = _FakeDB([(chunk, "medication-note.txt")])
    monkeypatch.setattr(rag, "_embed_query", lambda _: None)

    results = rag.retrieve_patient_chunks(db, patient, "blood pressure")

    assert results == [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "document_name": "medication-note.txt",
            "chunk_index": 0,
            "content": chunk.content,
            "score": 2.0,
        }
    ]
