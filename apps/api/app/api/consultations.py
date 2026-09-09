from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.keycloak import get_current_user, patient_subject
from app.config import settings
from app.db.session import get_db
from app.services.appointment_access import get_accessible_appointment
from app.services.consultation import get_consultation_url

router = APIRouter(prefix="/api/appointments", tags=["consultations"])


class ConsultationResponse(BaseModel):
    appointment_id: UUID
    join_url: str


def _roles(user: dict) -> set[str]:
    roles = set(user.get("realm_access", {}).get("roles", []))
    for client in user.get("resource_access", {}).values():
        roles.update(client.get("roles", []))
    return roles


@router.get("/{appointment_id}/consultation", response_model=ConsultationResponse)
def consultation(
    appointment_id: UUID,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsultationResponse:
    roles = _roles(user)
    subject = patient_subject(user)
    try:
        get_accessible_appointment(
            db,
            appointment_id=appointment_id,
            subject=subject,
            roles=roles,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        url = get_consultation_url(db, appointment_id, settings.jitsi_base_url)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ConsultationResponse(appointment_id=appointment_id, join_url=url)
