from datetime import date, time
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.keycloak import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Appointment, AuditEvent, Availability, Notification, Patient, Provider


PATIENT_SUBJECT = "integration-patient-subject"
PROVIDER_SUBJECT = "integration-provider-subject"
PROVIDER_ID = UUID("22222222-2222-2222-2222-222222222222")
PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
APPOINTMENT_DATE = date(2026, 9, 12)


def _build_database() -> tuple[object, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        Patient.__table__,
        Provider.__table__,
        Availability.__table__,
        Appointment.__table__,
        Notification.__table__,
        AuditEvent.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    db = Session(engine)
