from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from uuid import UUID

from minio import Minio
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import PatientDocument
from app.models.patient import Patient

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _safe_filename(filename: str) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:255] or "document"


def get_storage_client() -> Minio:
    endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def list_documents(db: Session, patient: Patient) -> list[PatientDocument]:
    return db.scalars(
        select(PatientDocument)
        .where(PatientDocument.patient_id == patient.id)
        .order_by(PatientDocument.created_at.desc())
    ).all()


def upload_document(
    db: Session,
    patient: Patient,
    *,
    filename: str,
    content_type: str,
    content: bytes,
    category: str | None,
    description: str | None,
) -> PatientDocument:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported document type")
    if not content:
        raise ValueError("Document is empty")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 10 MB limit")

    client = get_storage_client()
    ensure_bucket(client)

    safe_name = _safe_filename(filename)
    document = PatientDocument(
        patient_id=patient.id,
        object_key=f"patients/{patient.id}/{UUID(int=__import__('uuid').uuid4().int)}/{safe_name}",
        original_filename=safe_name,
        content_type=content_type,
        size_bytes=len(content),
        category=category,
        description=description,
    )
    client.put_object(
        settings.minio_bucket,
        document.object_key,
        BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, patient: Patient, document_id: UUID) -> PatientDocument:
    document = db.scalar(
        select(PatientDocument).where(
            PatientDocument.id == document_id,
            PatientDocument.patient_id == patient.id,
        )
    )
    if document is None:
        raise LookupError("Document not found")
    return document


def download_document(db: Session, patient: Patient, document_id: UUID) -> tuple[PatientDocument, bytes]:
    document = get_document(db, patient, document_id)
    client = get_storage_client()
    try:
        response = client.get_object(settings.minio_bucket, document.object_key)
        try:
            return document, response.read()
        finally:
            response.close()
            response.release_conn()
    except Exception as exc:  # noqa: BLE001 - normalize storage errors at service boundary.
        raise RuntimeError("Unable to read document from object storage") from exc


def delete_document(db: Session, patient: Patient, document_id: UUID) -> None:
    document = get_document(db, patient, document_id)
    client = get_storage_client()
    try:
        client.remove_object(settings.minio_bucket, document.object_key)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Unable to delete document from object storage") from exc
    db.delete(document)
    db.commit()
