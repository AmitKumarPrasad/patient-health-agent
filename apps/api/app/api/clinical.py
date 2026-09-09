from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.keycloak import get_current_user, patient_subject, require_roles
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.availability import Availability
from app.models.patient import Patient
from app.models.provider import Provider
from app.services.appointment_access import ADMIN_ROLE, PROVIDER_ROLE, PATIENT_ROLE
from app.services.appointment_lifecycle import transition_status
from app.services.appointment_tools import book_appointment
from app.services.audit import record_event
from app.services.notifications import (
    cancel_pending_appointment_reminders,
    schedule_appointment_reminders,
)

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


class AvailabilityRequest(BaseModel):
    available_date: date
    start_time: time
    end_time: time

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, value: time, info):
        start_time = info.data.get("start_time")
        if start_time is not None and value <= start_time:
            raise ValueError("Availability end time must be after start time")
        return value


class AppointmentCreateRequest(BaseModel):
    provider_id: UUID
    starts_at: str = Field(min_length=1, max_length=64)
    ends_at: str = Field(min_length=1, max_length=64)
    reason: str | None = Field(default=None, max_length=2000)


class StatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class AppointmentStatusResponse(BaseModel):
    id: UUID
    status: str


class AppointmentCreateResponse(BaseModel):
    id: UUID
    provider_id: UUID
    starts_at: str
    ends_at: str
    status: str
    reason: str | None


class NotificationProcessResponse(BaseModel):
    processed: int


def _roles(user: dict) -> set[str]:
    roles = set(user.get("realm_access", {}).get("roles", []))
    for client in user.get("resource_access", {}).values():
        roles.update(client.get("roles", []))
    return roles


def _provider_for_subject(db: Session, subject: str) -> Provider:
    provider = db.scalar(select(Provider).where(Provider.external_id == subject))
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    return provider


@router.get("/api/me", response_model=PatientResponse)
def me(
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> PatientResponse:
    patient = db.scalar(select(Patient).where(Patient.external_id == patient_subject(user)))
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    return PatientResponse.model_validate(patient, from_attributes=True)


@router.get("/api/me/provider", response_model=ProviderResponse)
def provider_me(
    user: dict = Depends(require_roles(PROVIDER_ROLE)),
    db: Session = Depends(get_db),
) -> ProviderResponse:
    provider = _provider_for_subject(db, patient_subject(user))
    return ProviderResponse.model_validate(provider, from_attributes=True)


@router.get("/api/providers", response_model=list[ProviderResponse])
def providers(
    specialty: str | None = Query(default=None, max_length=150),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[ProviderResponse]:
    query = select(Provider).order_by(Provider.last_name, Provider.first_name)
    if specialty and specialty.strip():
        query = query.where(Provider.specialty.ilike(f"%{specialty.strip()}%"))
    return [ProviderResponse.model_validate(item, from_attributes=True) for item in db.scalars(query).all()]


@router.get("/api/providers/{provider_id}/availability", response_model=list[AvailabilityResponse])
def provider_availability(
    provider_id: UUID,
    requested_date: date = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
) -> list[AvailabilityResponse]:
    if db.get(Provider, provider_id) is None:
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


@router.post("/api/appointments", response_model=AppointmentCreateResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    request: AppointmentCreateRequest,
    user: dict = Depends(require_roles(PATIENT_ROLE)),
    db: Session = Depends(get_db),
) -> AppointmentCreateResponse:
    try:
        starts_at = datetime.fromisoformat(request.starts_at)
        ends_at = datetime.fromisoformat(request.ends_at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Appointment times must be valid ISO-8601 timestamps") from exc

    patient = db.scalar(select(Patient).where(Patient.external_id == patient_subject(user)))
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    try:
        result = book_appointment(
            db,
            patient_id=patient.id,
            provider_id=request.provider_id,
            starts_at=starts_at,
            ends_at=ends_at,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    appointment = db.get(Appointment, UUID(result["id"]))
    if appointment is not None:
        schedule_appointment_reminders(db, appointment)

    return AppointmentCreateResponse(
        id=UUID(result["id"]),
        provider_id=UUID(result["provider_id"]),
        starts_at=result["starts_at"],
        ends_at=result["ends_at"],
        status=result["status"],
        reason=request.reason,
    )


@router.post("/api/providers/me/availability", response_model=AvailabilityResponse, status_code=status.HTTP_201_CREATED)
def create_provider_availability(
    request: AvailabilityRequest,
    user: dict = Depends(require_roles(PROVIDER_ROLE)),
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    provider = _provider_for_subject(db, patient_subject(user))
    existing = db.scalar(
        select(Availability).where(
            Availability.provider_id == provider.id,
            Availability.available_date == request.available_date,
            Availability.start_time == request.start_time,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Availability slot already exists")

    overlap = db.scalar(
        select(Availability).where(
            Availability.provider_id == provider.id,
            Availability.available_date == request.available_date,
            Availability.is_available.is_(True),
            Availability.start_time < request.end_time,
            Availability.end_time > request.start_time,
        )
    )
    if overlap is not None:
        raise HTTPException(status_code=409, detail="Availability slot overlaps an existing slot")

    item = Availability(
        provider_id=provider.id,
        available_date=request.available_date,
        start_time=request.start_time,
        end_time=request.end_time,
        is_available=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return AvailabilityResponse(
        id=item.id,
        provider_id=item.provider_id,
        available_date=item.available_date,
        start_time=item.start_time.isoformat(),
        end_time=item.end_time.isoformat(),
        is_available=item.is_available,
    )


@router.patch("/api/appointments/{appointment_id}/status", response_model=AppointmentStatusResponse)
def update_appointment_status(
    appointment_id: UUID,
    request: StatusRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentStatusResponse:
    roles = _roles(user)
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    subject = patient_subject(user)
    authorized = ADMIN_ROLE in roles
    if PATIENT_ROLE in roles:
        patient = db.scalar(select(Patient).where(Patient.external_id == subject))
        authorized = authorized or (
            patient is not None
            and appointment.patient_id == patient.id
            and request.status.lower() == AppointmentStatus.CANCELLED
        )
    if PROVIDER_ROLE in roles:
        provider = db.scalar(select(Provider).where(Provider.external_id == subject))
        authorized = authorized or (provider is not None and appointment.provider_id == provider.id)
    if not authorized:
        raise HTTPException(status_code=403, detail="You are not authorized to change this appointment")

    previous_status = str(appointment.status)
    try:
        updated = transition_status(db, appointment_id, request.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if str(updated.status) in {
        AppointmentStatus.CANCELLED,
        AppointmentStatus.COMPLETED,
        AppointmentStatus.NO_SHOW,
    }:
        cancel_pending_appointment_reminders(db, appointment_id)
    elif str(updated.status) == AppointmentStatus.CONFIRMED:
        schedule_appointment_reminders(db, updated)

    if previous_status != str(updated.status):
        actor_role = (
            ADMIN_ROLE
            if ADMIN_ROLE in roles
            else PROVIDER_ROLE
            if PROVIDER_ROLE in roles
            else PATIENT_ROLE
        )
        record_event(
            db,
            actor_subject=subject,
            actor_role=actor_role,
            action="appointment.status_change",
            resource_type="appointment",
            resource_id=str(appointment_id),
            patient_id=appointment.patient_id,
            metadata={"from_status": previous_status, "to_status": str(updated.status)},
        )

    return AppointmentStatusResponse(id=updated.id, status=str(updated.status))


@router.post("/api/admin/notifications/process", response_model=NotificationProcessResponse)
def process_notifications(
    user: dict = Depends(require_roles(ADMIN_ROLE)),
    db: Session = Depends(get_db),
) -> NotificationProcessResponse:
    from app.services.notifications import process_pending_notifications

    return NotificationProcessResponse(processed=process_pending_notifications(db))
