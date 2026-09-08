from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus


ROOM_PREFIX = "patient-health"


def _safe_room_id(appointment_id: UUID) -> str:
    digest = hashlib.sha256(str(appointment_id).encode("utf-8")).hexdigest()[:24]
    return f"{ROOM_PREFIX}-{digest}"


def consultation_url(base_url: str, room_id: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/{room_id}"


def get_consultation_url(db: Session, appointment_id: UUID, jitsi_base_url: str) -> str:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise LookupError("Appointment not found")
    if appointment.status not in (
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED,
    ):
        raise ValueError("Video consultation is only available for scheduled or confirmed appointments")
    return consultation_url(jitsi_base_url, _safe_room_id(appointment.id))
