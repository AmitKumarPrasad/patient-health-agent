from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.patient import Patient


PATIENT_ROLE = "patient"
PROVIDER_ROLE = "provider"
ADMIN_ROLE = "admin"


def list_accessible_appointments(
    db: Session,
    *,
    subject: str,
    roles: set[str],
) -> list[Appointment]:
    if ADMIN_ROLE in roles:
        return db.scalars(
            select(Appointment).order_by(Appointment.starts_at.desc())
        ).all()

    patient = db.scalar(select(Patient).where(Patient.external_id == subject))
    if PATIENT_ROLE in roles and patient is not None:
        return db.scalars(
            select(Appointment)
            .where(Appointment.patient_id == patient.id)
            .order_by(Appointment.starts_at.desc())
        ).all()

    raise PermissionError("No appointment access for authenticated user")


def get_accessible_appointment(
    db: Session,
    *,
    appointment_id: UUID,
    subject: str,
    roles: set[str],
) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise LookupError("Appointment not found")

    if ADMIN_ROLE in roles:
        return appointment

    patient = db.scalar(select(Patient).where(Patient.external_id == subject))
    if PATIENT_ROLE in roles and patient is not None and appointment.patient_id == patient.id:
        return appointment

    raise PermissionError("You are not authorized to access this appointment")
