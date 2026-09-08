from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.keycloak import get_current_user, patient_subject, require_roles
from app.db.session import get_db
from app.models.availability import Availability
from app.models.patient import Patient
from app.models.provider import Provider
from app.services.appointment_access import ADMIN_ROLE, PROVIDER_ROLE, PATIENT_ROLE
from app.services.appointment_lifecycle import transition_status

router = APIRouter(tags=["clinical"])


class PatientResponse(BaseModel):
    id: UUID
    external_id: str | None
    first_name: str
    last_name: str
    email: str | None
    phone: str | None


class ProviderResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    specialty: str
    email: str | None
    phone: str | None
    bio: str | None


class AvailabilityResponse(BaseModel):
    id: UUID
    provider_id: UUID
    available_date: date
    start_time: str
    end_time: str
    is_available: bool


class StatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)


def _roles(user: dict) -> set[str]:
    roles = set(user.get("realm_access", {}).get("roles", []))
    for client in user.get("resource_access", {}).values():
        roles.update(client.get("roles", []))
    return roles


@router.get("/api/me", response_model=PatientResponse)
def me(
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> PatientResponse:
    patient = db.scalar(select(Patient).where(Patient.external_id == patient_subject(user)))
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return PatientResponse.model_validate(patient, from_attributes=True)


@router.get("/api/providers", response_model=list[ProviderResponse])
def providers(
    specialty: str | None = Query(default=None, max_length=150),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[ProviderResponse]:
    query = select(Provider).order_by(Provider.last_name, Provider.first_name)
    if specialty:
        query = query.where(Provider.specialty.ilike(f"%{specialty.strip()}%"))
    return [ProviderResponse.model_validate(item, from_attributes=True) for item in db.scalars(query).all()]


@router.get("/api/providers/{provider_id}/availability", response_model=list[AvailabilityResponse])
def provider_availability(
    provider_id: UUID,
    requested_date: date = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[AvailabilityResponse]:
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    rows = db.scalars(
        select(Availability)
        .where(
            Availability.provider_id == provider_id,
            Availability.available_date == requested_date,
            Availability.is_available.is_(True),
        )
        .order_by(Availability.start_time)
    ).all()
    return [
        AvailabilityResponse(
            id=item.id,
            provider_id=item.provider_id,
            available_date=item.available_date,
            start_time=item.start_time.isoformat(),
            end_time=item.end_time.isoformat(),
            is_available=item.is_available,
        )
        for item in rows
    ]


@router.patch("/api/appointments/{appointment_id}/status")
def update_appointment_status(
    appointment_id: UUID,
    request: StatusRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = _roles(user)
    if not roles.intersection({PATIENT_ROLE, PROVIDER_ROLE, ADMIN_ROLE}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    appointment = db.get(__import__("app.models.appointment", fromlist=["Appointment"]).Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    subject = patient_subject(user)
    authorized = ADMIN_ROLE in roles
    if PATIENT_ROLE in roles:
        patient = db.scalar(select(Patient).where(Patient.external_id == subject))
        authorized = authorized or (patient is not None and appointment.patient_id == patient.id and request.status.lower() == "cancelled")
    if PROVIDER_ROLE in roles:
        provider = db.scalar(select(Provider).where(Provider.external_id == subject))
        authorized = authorized or (provider is not None and appointment.provider_id == provider.id)
    if not authorized:
        raise HTTPException(status_code=403, detail="You are not authorized to change this appointment")

    try:
        return transition_status(db, appointment_id, request.status).__dict__
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
