from __future__ import annotations

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.keycloak import patient_subject, require_roles
from app.db.session import get_db
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.services.audit import record_event
from app.services.documents import (
    MAX_DOCUMENT_BYTES,
    delete_document,
    download_document,
    list_documents,
    upload_document,
)

PATIENT_ROLE = "patient"

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str | None
    category: str | None
    description: str | None
    created_at: str


def _patient_for_subject(db: Session, subject: str) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.external_id == subject))
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return patient


def _serialize(document: PatientDocument) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        sha256=document.sha256,
        category=document.category,
        description=document.description,
        created_at=document.created_at.isoformat(),
    )


def _record_patient_document_event(
    db: Session,
    *,
    subject: str,
    action: str,
    patient: Patient,
    document: PatientDocument | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    outcome: str = "success",
    error_message: str | None = None,
) -> None:
    try:
        record_event(
            db,
            actor_subject=subject,
            actor_role=PATIENT_ROLE,
            action=action,
            resource_type="patient_document",
            resource_id=resource_id or (str(document.id) if document is not None else None),
            patient_id=patient.id,
            metadata=metadata,
            outcome=outcome,
            error_message=error_message,
        )
    except Exception:  # noqa: BLE001 - audit failure must never mask the document request outcome.
        db.rollback()


@router.get("", response_model=list[DocumentResponse])
def list_patient_documents(
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    subject = patient_subject(user)
    patient = _patient_for_subject(db, subject)
    documents = list_documents(db, patient)
    _record_patient_document_event(
        db,
        subject=subject,
        action="record.list",
        patient=patient,
        metadata={"document_count": len(documents)},
    )
    return [_serialize(item) for item in documents]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_patient_document(
    file: UploadFile = File(...),
    category: str | None = Form(default=None, max_length=100),
    description: str | None = Form(default=None, max_length=2000),
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    subject = patient_subject(user)
    patient = _patient_for_subject(db, subject)
    content_type = file.content_type or "application/octet-stream"

    if file.size is not None and file.size > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=400, detail="Document exceeds the 10 MB limit")

    buffer = BytesIO()
    total_size = 0
    while True:
        chunk = file.file.read(1024 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=400, detail="Document exceeds the 10 MB limit")
        buffer.write(chunk)
    content = buffer.getvalue()

    try:
        document = upload_document(
            db,
            patient,
            filename=file.filename or "document",
            content_type=content_type,
            content=content,
            category=category.strip() if category else None,
            description=description.strip() if description else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        buffer.close()

    _record_patient_document_event(
        db,
        subject=subject,
        action="record.create",
        patient=patient,
        document=document,
        metadata={
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
        },
    )
    return _serialize(document)


@router.get("/{document_id}")
def get_patient_document(
    document_id: UUID,
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> Response:
    subject = patient_subject(user)
    patient = _patient_for_subject(db, subject)
    try:
        document, content = download_document(db, patient, document_id)
    except LookupError as exc:
        _record_patient_document_event(
            db,
            subject=subject,
            action="record.read",
            patient=patient,
            resource_id=str(document_id),
            outcome="failure",
            error_message="Document not found",
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        _record_patient_document_event(
            db,
            subject=subject,
            action="record.read",
            patient=patient,
            resource_id=str(document_id),
            outcome="failure",
            error_message="Document retrieval failed",
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _record_patient_document_event(
        db,
        subject=subject,
        action="record.read",
        patient=patient,
        document=document,
        metadata={
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
        },
    )
    return Response(
        content=content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_patient_document(
    document_id: UUID,
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> Response:
    subject = patient_subject(user)
    patient = _patient_for_subject(db, subject)
    try:
        document = next(item for item in list_documents(db, patient) if item.id == document_id)
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc

    try:
        delete_document(db, patient, document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _record_patient_document_event(
        db,
        subject=subject,
        action="record.delete",
        patient=patient,
        document=document,
        metadata={"content_type": document.content_type, "size_bytes": document.size_bytes},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
