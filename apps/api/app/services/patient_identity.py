from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient


def get_patient_by_external_id(db: Session, external_id: str) -> Patient | None:
    external_id = external_id.strip()
    if not external_id:
        raise ValueError("External identity is required")
    return db.scalar(select(Patient).where(Patient.external_id == external_id))


def require_patient_by_external_id(db: Session, external_id: str) -> Patient:
    patient = get_patient_by_external_id(db, external_id)
    if patient is None:
        raise LookupError("Authenticated patient is not registered")
    return patient
