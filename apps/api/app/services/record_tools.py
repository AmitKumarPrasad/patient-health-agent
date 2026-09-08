from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.services.documents import download_document
from app.services.rag import retrieve_patient_chunks


def _patient_for_subject(db: Session, subject: str) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.external_id == subject))
    if patient is None:
        raise LookupError("Authenticated patient is not registered")
    return patient


def search_patient_documents(request: str, subject: str, *, limit: int = 10) -> list[dict[str, str]]:
    query_text = request.strip().lower()
    with SessionLocal() as db:
        patient = _patient_for_subject(db, subject)
        query = select(PatientDocument).where(PatientDocument.patient_id == patient.id)
        documents = db.scalars(query.order_by(PatientDocument.created_at.desc()).limit(limit)).all()

        if not query_text:
            return [_metadata(item) for item in documents]

        terms = [term for term in query_text.split() if len(term) > 2]
        matched = []
        for item in documents:
            haystack = " ".join(
                [
                    item.original_filename or "",
                    item.category or "",
                    item.description or "",
                    item.content_type or "",
                ]
            ).lower()
            if any(term in haystack for term in terms):
                matched.append(_metadata(item))
        return matched


def search_patient_record_content(request: str, subject: str, *, limit: int = 5) -> list[dict]:
    with SessionLocal() as db:
        patient = _patient_for_subject(db, subject)
        return retrieve_patient_chunks(db, patient, request.strip(), limit=limit)


def get_patient_document_text(document_id: str, subject: str) -> str:
    from uuid import UUID

    with SessionLocal() as db:
        patient = _patient_for_subject(db, subject)
        document, content = download_document(db, patient, UUID(document_id))
        if document.content_type != "text/plain":
            return "Only text/plain documents can be read directly by the demo agent. Use semantic record search for indexed PDF content."
        return content[:50000].decode("utf-8", errors="replace")


def _metadata(item: PatientDocument) -> dict[str, str]:
    return {
        "id": str(item.id),
        "original_filename": item.original_filename,
        "content_type": item.content_type,
        "size_bytes": str(item.size_bytes),
        "sha256": item.sha256 or "",
        "category": item.category or "",
        "description": item.description or "",
        "created_at": item.created_at.isoformat() if item.created_at else "",
    }
