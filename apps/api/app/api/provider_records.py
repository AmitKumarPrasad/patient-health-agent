from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.keycloak import patient_subject, require_roles
from app.db.session import get_db
from app.models.document import PatientDocument
from app.services.audit import record_event
from app.services.appointment_access import PROVIDER_ROLE
from app.services.documents import download_document
from app.services.provider_identity import require_provider_by_external_id
from app.services.provider_records import list_provider_patient_documents, authorize_provider_patient

router = APIRouter(prefix="/api/provider", tags=["provider-records"])


class ProviderDocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    category: str | None
    description: str | None
    created_at: str


def _serialize(document: PatientDocument) -> ProviderDocumentResponse:
    return ProviderDocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        category=document.category,
        description=document.description,
        created_at=document.created_at.isoformat(),
    )


@router.get("/patients/{patient_id}/records", response_model=list[ProviderDocumentResponse])
def provider_patient_records(
    patient_id: UUID,
    user: dict = Depends(require_roles(PROVIDER_ROLE)),
    db: Session = Depends(get_db),
) -> list[ProviderDocumentResponse]:
    provider = require_provider_by_external_id(db, patient_subject(user))
    try:
        documents = list_provider_patient_documents(db, provider, patient_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_event(
        db,
        actor_subject=patient_subject(user),
        actor_role=PROVIDER_ROLE,
        action="record.list",
        resource_type="patient_document",
        patient_id=patient_id,
        metadata={"document_count": len(documents)},
    )
    return [_serialize(document) for document in documents]


@router.get("/patients/{patient_id}/records/{document_id}")
def provider_patient_record(
    patient_id: UUID,
    document_id: UUID,
    user: dict = Depends(require_roles(PROVIDER_ROLE)),
    db: Session = Depends(get_db),
):
    provider = require_provider_by_external_id(db, patient_subject(user))
    try:
        patient = authorize_provider_patient(db, provider, patient_id)
        document = db.scalar(
            select(PatientDocument).where(
                PatientDocument.id == document_id,
                PatientDocument.patient_id == patient.id,
            )
        )
        if document is None:
            raise LookupError("Document not found")
        _, content = download_document(db, patient, document.id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record_event(
        db,
        actor_subject=patient_subject(user),
        actor_role=PROVIDER_ROLE,
        action="record.read",
        resource_type="patient_document",
        resource_id=str(document.id),
        patient_id=patient_id,
        metadata={"content_type": document.content_type},
    )
    return {"document": _serialize(document), "content": content.decode("utf-8", errors="replace") if document.content_type == "text/plain" else None}
