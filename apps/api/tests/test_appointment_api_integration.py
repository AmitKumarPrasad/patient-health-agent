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
from app.models import Availability, Notification, Patient, Provider


PATIENT_SUBJECT = "integration-patient-subject"
PROVIDER_ID = UUID("22222222-2222-2222-2222-222222222222")
PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
APPOINTMENT_DATE = date(2026, 9, 10)


def _build_database() -> tuple[object, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add_all(
        [
            Patient(
                id=PATIENT_ID,
                external_id=PATIENT_SUBJECT,
                first_name="Demo",
                last_name="Patient",
                email="demo.patient@example.test",
            ),
            Provider(
                id=PROVIDER_ID,
                external_id="integration-provider-subject",
                first_name="Demo",
                last_name="Provider",
                specialty="Dermatology",
                email="demo.provider@example.test",
            ),
            Availability(
                provider_id=PROVIDER_ID,
                available_date=APPOINTMENT_DATE,
                start_time=time(10, 0),
                end_time=time(10, 30),
                is_available=True,
            ),
        ]
    )
    db.commit()
    return engine, db


def test_patient_appointment_api_flow() -> None:
    engine, db = _build_database()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": PATIENT_SUBJECT,
        "realm_access": {"roles": ["patient"]},
    }
    try:
        with TestClient(app) as client:
            me = client.get("/api/me")
            assert me.status_code == 200
            assert me.json()["external_id"] == PATIENT_SUBJECT

            providers = client.get("/api/providers", params={"specialty": "dermatology"})
            assert providers.status_code == 200
            assert providers.json()[0]["id"] == str(PROVIDER_ID)

            availability = client.get(
                f"/api/providers/{PROVIDER_ID}/availability",
                params={"requested_date": APPOINTMENT_DATE.isoformat()},
            )
            assert availability.status_code == 200
            assert len(availability.json()) == 1
            assert availability.json()[0]["start_time"] == "10:00:00"

            booking = client.post(
                "/api/appointments",
                json={
                    "provider_id": str(PROVIDER_ID),
                    "starts_at": "2026-09-10T10:00:00+00:00",
                    "ends_at": "2026-09-10T10:30:00+00:00",
                    "reason": "Routine consultation",
                },
            )
            assert booking.status_code == 201
            appointment = booking.json()
            assert appointment["provider_id"] == str(PROVIDER_ID)
            assert appointment["status"] == "scheduled"

            second_booking = client.post(
                "/api/appointments",
                json={
                    "provider_id": str(PROVIDER_ID),
                    "starts_at": "2026-09-10T10:00:00+00:00",
                    "ends_at": "2026-09-10T10:30:00+00:00",
                },
            )
            assert second_booking.status_code == 409
            assert "already booked" in second_booking.json()["detail"]

            cancelled = client.patch(
                f"/api/appointments/{appointment['id']}/status",
                json={"status": "cancelled"},
            )
            assert cancelled.status_code == 200
            assert cancelled.json()["status"] == "cancelled"

            notifications = db.query(Notification).all()
            assert len(notifications) == 2
            assert {item.status for item in notifications} == {"failed"}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        db.close()
        engine.dispose()
