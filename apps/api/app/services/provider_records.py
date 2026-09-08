from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.models.provider import Provider


ALLOWED_RECORD_APPOINTMENT_STATUSES = {
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.COMPLETED,
}


def authorize_provider_patient(db: Session, provider: Provider, patient_id: UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise LookupError("Patient not found")

    appointment = db.scalar(
        select(Appointment).where(
            Appointment.provider_id == provider.id,
            Appointment.patient_id == patient.id,
            Appointment.status.in_(ALLOWED_RECORD_APPOINTMENT_STATUSES),
        )
    )
    if appointment is None:
        raise PermissionError("Provider is not authorized for this patient's records")
    return patient


def list_provider_patient_documents(
    db: Session, provider: Provider, patient_id: UUID
) -> list[PatientDocument]:
    patient = authorize_provider_patient(db, provider, patient_id)
    return db.scalars(
        select(PatientDocument)
        .where(PatientDocument.patient_id == patient.id)
        .order_by(PatientDocument.created_at.desc())
    ).all()
