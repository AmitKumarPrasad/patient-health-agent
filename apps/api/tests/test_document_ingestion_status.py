from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.services import documents


def _db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, PatientDocument.__table__])
    return Session(engine)


def _document(db: Session) -> PatientDocument:
    patient = Patient(first_name="Test", last_name="Patient")
    db.add(patient)
    db.flush()
    item = PatientDocument(
        patient_id=patient.id,
        object_key="patients/test/note.txt",
        original_filename="note.txt",
        content_type="text/plain",
        size_bytes=5,
        ingestion_status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_index_document_marks_ready_and_records_chunk_count(monkeypatch) -> None:
    with _db() as db:
        item = _document(db)
        monkeypatch.setattr(documents, "index_document", lambda *args: 3)

        indexed = documents._index_document(db, item, b"hello")

        refreshed = db.scalar(select(PatientDocument).where(PatientDocument.id == item.id))
        assert indexed == 3
        assert refreshed is not None
        assert refreshed.ingestion_status == "ready"
        assert refreshed.indexed_chunks == 3
        assert refreshed.indexed_at is not None
        assert refreshed.ingestion_error is None


def test_index_document_marks_failed_without_leaking_exception(monkeypatch) -> None:
    with _db() as db:
        item = _document(db)

        def fail(*args):
            raise RuntimeError("embedding provider unavailable")

        monkeypatch.setattr(documents, "index_document", fail)

        indexed = documents._index_document(db, item, b"hello")

        refreshed = db.scalar(select(PatientDocument).where(PatientDocument.id == item.id))
        assert indexed == 0
        assert refreshed is not None
        assert refreshed.ingestion_status == "failed"
        assert refreshed.indexed_chunks == 0
        assert refreshed.indexed_at is None
        assert refreshed.ingestion_error == "embedding provider unavailable"
