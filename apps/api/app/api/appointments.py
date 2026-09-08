from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.keycloak import get_current_user, patient_subject
from app.db.session import get_db
from app.services.appointment_access import (
    get_accessible_appointment,
    list_accessible_appointments,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


class AppointmentResponse(BaseModel):
    id: UUID
    patient_id: UUID
    provider_id: UUID
    starts_at: str
    ends_at: str
    status: str
    appointment_type: str
    reason: str | None


def _roles(user: dict) -> set[str]:
    roles = set(user.get("realm_access", {}).get("roles", []))
    for client in user.get("resource_access", {}).values():
        roles.update(client.get("roles", []))
    return roles


def _serialize(appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        provider_id=appointment.provider_id,
        starts_at=appointment.starts_at.isoformat(),
        ends_at=appointment.ends_at.isoformat(),
        status=str(appointment.status),
        appointment_type=appointment.appointment_type,
        reason=appointment.reason,
    )


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AppointmentResponse]:
    try:
        appointments = list_accessible_appointments(
            db, subject=patient_subject(user), roles=_roles(user)
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [_serialize(item) for item in appointments]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: UUID,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentResponse:
    try:
        appointment = get_accessible_appointment(
            db,
            appointment_id=appointment_id,
            subject=patient_subject(user),
            roles=_roles(user),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _serialize(appointment)
