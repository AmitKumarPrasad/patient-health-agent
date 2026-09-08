from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}


def transition_status(db: Session, appointment_id: UUID, new_status: str) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise LookupError("Appointment not found")

    new_status = new_status.strip().lower()
    if new_status not in {item.value for item in AppointmentStatus}:
        raise ValueError("Invalid appointment status")

    current_status = str(appointment.status)
    if new_status == current_status:
        return appointment
    if new_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise ValueError(f"Cannot transition appointment from {current_status} to {new_status}")

    appointment.status = new_status
    db.commit()
    db.refresh(appointment)
    return appointment
