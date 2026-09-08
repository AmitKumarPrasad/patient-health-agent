from __future__ import annotations

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
from app.services.documents import download_document, delete_document, list_documents, upload_document

PATIENT_ROLE = "patient"

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
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
        category=document.category,
        description=document.description,
        created_at=document.created_at.isoformat(),
    )


@router.get("", response_model=list[DocumentResponse])
def list_patient_documents(
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    patient = _patient_for_subject(db, patient_subject(user))
    return [_serialize(item) for item in list_documents(db, patient)]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_patient_document(
    file: UploadFile = File(...),
    category: str | None = Form(default=None, max_length=100),
    description: str | None = Form(default=None, max_length=2000),
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    patient = _patient_for_subject(db, patient_subject(user))
    content_type = file.content_type or "application/octet-stream"
    content = file.file.read()
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
    return _serialize(document)


@router.get("/{document_id}")
def get_patient_document(
    document_id: UUID,
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> Response:
    patient = _patient_for_subject(db, patient_subject(user))
    try:
        document, content = download_document(db, patient, document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_patient_document(
    document_id: UUID,
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> Response:
    patient = _patient_for_subject(db, patient_subject(user))
    try:
        delete_document(db, patient, document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
