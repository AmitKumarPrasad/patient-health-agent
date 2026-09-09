from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.clinical import StatusRequest, update_appointment_status
from app.db.base import Base
from app.models import Appointment, Notification, Patient, Provider


PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_PATIENT_ID = UUID("33333333-3333-3333-3333-333333333333")
PROVIDER_ID = UUID("22222222-2222-2222-2222-222222222222")
APPOINTMENT_ID = UUID("44444444-4444-4444-4444-444444444444")
OTHER_APPOINTMENT_ID = UUID("55555555-5555-5555-5555-555555555555")
PATIENT_SUBJECT = "lifecycle-patient-subject"
OTHER_PATIENT_SUBJECT = "lifecycle-other-patient-subject"
PROVIDER_SUBJECT = "lifecycle-provider-subject"


def _build_database() -> tuple[object, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[Patient.__table__, Provider.__table__, Appointment.__table__, Notification.__table__],
    )
    db = Session(engine)
    start = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 12, 10, 30, tzinfo=timezone.utc)
    db.add_all(
        [
            Patient(
                id=PATIENT_ID,
                external_id=PATIENT_SUBJECT,
                first_name="Demo",
                last_name="Patient",
                email="patient@example.test",
            ),
            Patient(
                id=OTHER_PATIENT_ID,
                external_id=OTHER_PATIENT_SUBJECT,
                first_name="Other",
                last_name="Patient",
                email="other@example.test",
            ),
            Provider(
                id=PROVIDER_ID,
                external_id=PROVIDER_SUBJECT,
                first_name="Demo",
                last_name="Provider",
                specialty="Dermatology",
                email="provider@example.test",
            ),
            Appointment(
                id=APPOINTMENT_ID,
                patient_id=PATIENT_ID,
                provider_id=PROVIDER_ID,
                starts_at=start,
                ends_at=end,
                status="scheduled",
            ),
            Appointment(
                id=OTHER_APPOINTMENT_ID,
                patient_id=OTHER_PATIENT_ID,
                provider_id=PROVIDER_ID,
                starts_at=datetime(2026, 9, 12, 11, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 9, 12, 11, 30, tzinfo=timezone.utc),
                status="scheduled",
            ),
        ]
    )
    db.commit()
    return engine, db


def _user(subject: str, role: str) -> dict:
    return {"sub": subject, "realm_access": {"roles": [role]}}


def test_patient_can_cancel_own_appointment_but_not_other_patient() -> None:
    engine, db = _build_database()
    try:
        cancelled = update_appointment_status(
            APPOINTMENT_ID,
            StatusRequest(status="cancelled"),
            _user(PATIENT_SUBJECT, "patient"),
            db,
        )
        assert cancelled.status == "cancelled"

        with pytest.raises(HTTPException) as exc_info:
            update_appointment_status(
                OTHER_APPOINTMENT_ID,
                StatusRequest(status="cancelled"),
                _user(PATIENT_SUBJECT, "patient"),
                db,
            )
        assert exc_info.value.status_code == 403
    finally:
        db.close()
        engine.dispose()


def test_patient_cannot_change_own_appointment_to_provider_status() -> None:
    engine, db = _build_database()
    try:
        with pytest.raises(HTTPException) as exc_info:
            update_appointment_status(
                APPOINTMENT_ID,
                StatusRequest(status="confirmed"),
                _user(PATIENT_SUBJECT, "patient"),
                db,
            )
        assert exc_info.value.status_code == 403
    finally:
        db.close()
        engine.dispose()


def test_provider_can_progress_assigned_appointment() -> None:
    engine, db = _build_database()
    try:
        confirmed = update_appointment_status(
            APPOINTMENT_ID,
            StatusRequest(status="confirmed"),
            _user(PROVIDER_SUBJECT, "provider"),
            db,
        )
        assert confirmed.status == "confirmed"

        completed = update_appointment_status(
            APPOINTMENT_ID,
            StatusRequest(status="completed"),
            _user(PROVIDER_SUBJECT, "provider"),
            db,
        )
        assert completed.status == "completed"
    finally:
        db.close()
        engine.dispose()


def test_provider_cannot_modify_appointment_outside_assignment() -> None:
    engine, db = _build_database()
    try:
        with pytest.raises(HTTPException) as exc_info:
            update_appointment_status(
                OTHER_APPOINTMENT_ID,
                StatusRequest(status="confirmed"),
                _user("different-provider-subject", "provider"),
                db,
            )
        assert exc_info.value.status_code == 403
    finally:
        db.close()
        engine.dispose()


def test_lifecycle_rejects_invalid_status_transition() -> None:
    engine, db = _build_database()
    try:
        with pytest.raises(HTTPException) as exc_info:
            update_appointment_status(
                APPOINTMENT_ID,
                StatusRequest(status="completed"),
                _user(PROVIDER_SUBJECT, "provider"),
                db,
            )
        assert exc_info.value.status_code == 400
        assert "Cannot transition appointment" in exc_info.value.detail
    finally:
        db.close()
        engine.dispose()
