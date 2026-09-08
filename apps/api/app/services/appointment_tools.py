from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.availability import Availability
from app.models.patient import Patient
from app.models.provider import Provider


def search_providers(db: Session, specialty: str) -> list[dict[str, str]]:
    specialty = specialty.strip()
    if not specialty:
        raise ValueError("Specialty is required")

    providers = db.scalars(
        select(Provider)
        .where(Provider.specialty.ilike(f"%{specialty}%"))
        .order_by(Provider.last_name, Provider.first_name)
    ).all()
    return [
        {
            "id": str(provider.id),
            "name": f"{provider.first_name} {provider.last_name}",
            "specialty": provider.specialty,
        }
        for provider in providers
    ]


def get_available_slots(
    db: Session,
    provider_id: UUID,
    requested_date: date,
) -> list[dict[str, str]]:
    slots = db.scalars(
        select(Availability)
        .where(
            Availability.provider_id == provider_id,
            Availability.available_date == requested_date,
            Availability.is_available.is_(True),
        )
        .order_by(Availability.start_time)
    ).all()

    booked = db.scalars(
        select(Appointment)
        .where(
            Appointment.provider_id == provider_id,
            Appointment.starts_at >= datetime.combine(requested_date, time.min, tzinfo=timezone.utc),
            Appointment.starts_at < datetime.combine(requested_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
            Appointment.status.in_((AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)),
        )
    ).all()
    booked_starts = {appointment.starts_at for appointment in booked}

    return [
        {
            "start": datetime.combine(requested_date, slot.start_time, tzinfo=timezone.utc).isoformat(),
            "end": datetime.combine(requested_date, slot.end_time, tzinfo=timezone.utc).isoformat(),
        }
        for slot in slots
        if datetime.combine(requested_date, slot.start_time, tzinfo=timezone.utc) not in booked_starts
    ]


def book_appointment(
    db: Session,
    patient_id: UUID,
    provider_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    reason: str | None = None,
) -> dict[str, str]:
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        raise ValueError("Appointment times must include a timezone")
    if ends_at <= starts_at:
        raise ValueError("Appointment end must be after appointment start")

    patient = db.get(Patient, patient_id)
    provider = db.get(Provider, provider_id)
    if patient is None:
        raise ValueError("Patient not found")
    if provider is None:
        raise ValueError("Provider not found")

    requested_date = starts_at.astimezone(timezone.utc).date()
    appointment_start_utc = starts_at.astimezone(timezone.utc)
    appointment_end_utc = ends_at.astimezone(timezone.utc)

    available = db.scalars(
        select(Availability)
        .where(
            Availability.provider_id == provider_id,
            Availability.available_date == requested_date,
            Availability.is_available.is_(True),
            Availability.start_time <= appointment_start_utc.time(),
            Availability.end_time >= appointment_end_utc.time(),
        )
        .with_for_update()
    ).first()
    if available is None:
        raise ValueError("The requested time is not in the provider's available schedule")

    overlap = db.scalar(
        select(Appointment).where(
            Appointment.provider_id == provider_id,
            Appointment.status.in_((AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)),
            Appointment.starts_at < appointment_end_utc,
            Appointment.ends_at > appointment_start_utc,
        ).limit(1)
    )
    if overlap is not None:
        raise ValueError("The requested provider time is already booked")

    appointment = Appointment(
        patient_id=patient_id,
        provider_id=provider_id,
        starts_at=starts_at,
        ends_at=ends_at,
        status=AppointmentStatus.SCHEDULED,
        reason=reason,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "id": str(appointment.id),
        "patient_id": str(appointment.patient_id),
        "provider_id": str(appointment.provider_id),
        "starts_at": appointment.starts_at.isoformat(),
        "ends_at": appointment.ends_at.isoformat(),
        "status": appointment.status,
    }
