from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.consultations import consultation
from app.db.base import Base
from app.models import Appointment, Patient, Provider

PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_PATIENT_ID = UUID("33333333-3333-3333-3333-333333333333")
PROVIDER_ID = UUID("22222222-2222-2222-2222-222222222222")
APPOINTMENT_ID = UUID("44444444-4444-4444-4444-444444444444")
PATIENT_SUBJECT = "consultation-patient-subject"
OTHER_PATIENT_SUBJECT = "other-patient-subject"
PROVIDER_SUBJECT = "consultation-provider-subject"


def _build_database() -> tuple[object, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[Patient.__table__, Provider.__table__, Appointment.__table__],
    )
    db = Session(engine)
    db.add_all(
        [
            Patient(id=PATIENT_ID, external_id=PATIENT_SUBJECT, first_name="Demo", last_name="Patient", email="patient@example.test"),
            Patient(id=OTHER_PATIENT_ID, external_id=OTHER_PATIENT_SUBJECT, first_name="Other", last_name="Patient", email="other@example.test"),
            Provider(id=PROVIDER_ID, external_id=PROVIDER_SUBJECT, first_name="Demo", last_name="Provider", specialty="General Medicine", email="provider@example.test"),
            Appointment(
                id=APPOINTMENT_ID,
                patient_id=PATIENT_ID,
                provider_id=PROVIDER_ID,
                starts_at=datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 9, 12, 10, 30, tzinfo=timezone.utc),
                status="scheduled",
                appointment_type="consultation",
            ),
        ]
    )
    db.commit()
    return engine, db


def _user(subject: str, role: str) -> dict:
    return {"sub": subject, "realm_access": {"roles": [role]}}


def test_patient_can_get_own_consultation_url() -> None:
    engine, db = _build_database()
    try:
        result = consultation(APPOINTMENT_ID, user=_user(PATIENT_SUBJECT, "patient"), db=db)
        assert result.appointment_id == APPOINTMENT_ID
        assert result.join_url.startswith("http://localhost:8443/patient-health-")
    finally:
        db.close()
        engine.dispose()


def test_other_patient_cannot_get_consultation_url() -> None:
    engine, db = _build_database()
    try:
        try:
            consultation(APPOINTMENT_ID, user=_user(OTHER_PATIENT_SUBJECT, "patient"), db=db)
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("Expected consultation access to be denied")
    finally:
        db.close()
        engine.dispose()


def test_provider_can_get_assigned_consultation_url() -> None:
    engine, db = _build_database()
    try:
        result = consultation(APPOINTMENT_ID, user=_user(PROVIDER_SUBJECT, "provider"), db=db)
        assert result.appointment_id == APPOINTMENT_ID
        assert result.join_url.startswith("http://localhost:8443/patient-health-")
    finally:
        db.close()
        engine.dispose()


def test_cancelled_appointment_cannot_start_consultation() -> None:
    engine, db = _build_database()
    try:
        appointment = db.get(Appointment, APPOINTMENT_ID)
        assert appointment is not None
        appointment.status = "cancelled"
        db.commit()

        try:
            consultation(APPOINTMENT_ID, user=_user(PATIENT_SUBJECT, "patient"), db=db)
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("Expected cancelled consultation to be rejected")
    finally:
        db.close()
        engine.dispose()
