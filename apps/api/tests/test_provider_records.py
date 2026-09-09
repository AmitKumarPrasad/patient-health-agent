from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Appointment, Patient, PatientDocument, Provider
from app.services.provider_records import (
    authorize_provider_patient,
    list_provider_patient_documents,
)


PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_PATIENT_ID = UUID("33333333-3333-3333-3333-333333333333")
PROVIDER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _build_database() -> tuple[object, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[Patient.__table__, Provider.__table__, Appointment.__table__, PatientDocument.__table__],
    )
    db = Session(engine)
    start = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 12, 10, 30, tzinfo=timezone.utc)
    db.add_all(
        [
            Patient(id=PATIENT_ID, external_id="patient-subject", first_name="Demo", last_name="Patient", email="patient@example.test"),
            Patient(id=OTHER_PATIENT_ID, external_id="other-patient-subject", first_name="Other", last_name="Patient", email="other@example.test"),
            Provider(id=PROVIDER_ID, external_id="provider-subject", first_name="Demo", last_name="Provider", specialty="Cardiology", email="provider@example.test"),
            Appointment(
                id=UUID("44444444-4444-4444-4444-444444444444"),
                patient_id=PATIENT_ID,
                provider_id=PROVIDER_ID,
                starts_at=start,
                ends_at=end,
                status="scheduled",
            ),
            PatientDocument(
                id=UUID("66666666-6666-6666-6666-666666666666"),
                patient_id=PATIENT_ID,
                object_key="patients/demo/report.txt",
                original_filename="report.txt",
                content_type="text/plain",
                size_bytes=42,
                sha256="a" * 64,
                category="lab report",
                description="Demo lab report",
            ),
            PatientDocument(
                id=UUID("77777777-7777-7777-7777-777777777777"),
                patient_id=OTHER_PATIENT_ID,
                object_key="patients/other/report.txt",
                original_filename="other-report.txt",
                content_type="text/plain",
                size_bytes=24,
                sha256="b" * 64,
            ),
        ]
    )
    db.commit()
    return engine, db


def test_provider_can_access_records_for_an_active_patient() -> None:
    engine, db = _build_database()
    try:
        provider = db.get(Provider, PROVIDER_ID)
        assert provider is not None
        patient = authorize_provider_patient(db, provider, PATIENT_ID)
        assert patient.id == PATIENT_ID
        documents = list_provider_patient_documents(db, provider, PATIENT_ID)
        assert [item.original_filename for item in documents] == ["report.txt"]
    finally:
        db.close()
        engine.dispose()


def test_provider_cannot_access_patient_without_active_appointment() -> None:
    engine, db = _build_database()
    try:
        provider = db.get(Provider, PROVIDER_ID)
        assert provider is not None
        with pytest.raises(PermissionError, match="not authorized"):
            authorize_provider_patient(db, provider, OTHER_PATIENT_ID)
    finally:
        db.close()
        engine.dispose()


def test_provider_is_not_authorized_for_unknown_patient() -> None:
    engine, db = _build_database()
    try:
        provider = db.get(Provider, PROVIDER_ID)
        assert provider is not None
        with pytest.raises(LookupError, match="Patient not found"):
            authorize_provider_patient(db, provider, uuid4())
    finally:
        db.close()
        engine.dispose()


def test_completed_appointment_still_allows_record_access() -> None:
    engine, db = _build_database()
    try:
        appointment = db.get(Appointment, UUID("44444444-4444-4444-4444-444444444444"))
        assert appointment is not None
        appointment.status = "completed"
        db.commit()
        provider = db.get(Provider, PROVIDER_ID)
        assert provider is not None
        assert authorize_provider_patient(db, provider, PATIENT_ID).id == PATIENT_ID
    finally:
        db.close()
        engine.dispose()
