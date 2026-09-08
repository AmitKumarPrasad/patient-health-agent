from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.record_agent import invoke_record_agent
from app.auth.keycloak import patient_subject, require_roles
from app.services.appointment_access import PATIENT_ROLE
from app.services.record_tools import get_patient_document_text, search_patient_documents

router = APIRouter(prefix="/api/records", tags=["records"])


class RecordAgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class RecordAgentResponse(BaseModel):
    response: str


class DocumentSearchResponse(BaseModel):
    documents: list[dict[str, str]]


class DocumentTextResponse(BaseModel):
    document_id: str
    text: str


@router.post("/assistant", response_model=RecordAgentResponse)
def record_assistant(
    request: RecordAgentRequest,
    user: dict = Depends(require_roles(PATIENT_ROLE)),
) -> RecordAgentResponse:
    try:
        response = invoke_record_agent(request.message, patient_subject(user))
    except LookupError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RecordAgentResponse(response=response)


@router.get("/search", response_model=DocumentSearchResponse)
def search_records(
    q: str = "",
    user: dict = Depends(require_roles(PATIENT_ROLE)),
) -> DocumentSearchResponse:
    try:
        documents = search_patient_documents(q, patient_subject(user))
    except LookupError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return DocumentSearchResponse(documents=documents)


@router.get("/{document_id}/text", response_model=DocumentTextResponse)
def get_record_text(
    document_id: str,
    user: dict = Depends(require_roles(PATIENT_ROLE)),
) -> DocumentTextResponse:
    try:
        text = get_patient_document_text(document_id, patient_subject(user))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentTextResponse(document_id=document_id, text=text)
