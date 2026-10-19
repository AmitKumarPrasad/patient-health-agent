from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import clinical
from app.auth.keycloak import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Patient


PATIENT_SUBJECT = "error-disclosure-patient"
PATIENT_ID = UUID("11111111-1111-4111-8111-111111111111")
PROVIDER_ID = UUID("22222222-2222-4222-8222-222222222222")


def test_booking_failure_does_not_disclose_internal_exception(monkeypatch) -> None:
    """Unexpected booking failures must return a generic error, never DB/credential details."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__])
    db = Session(engine)
    db.add(
        Patient(
            id=PATIENT_ID,
            external_id=PATIENT_SUBJECT,
            first_name="Synthetic",
            last_name="Patient",
            email="synthetic.patient@example.test",
            phone="+10000000000",
        )
    )
    db.commit()

    def _fail_booking(*args, **kwargs):
        raise RuntimeError("connection failed token=synthetic-secret host=db.internal.test")

    monkeypatch.setattr(clinical, "book_appointment", _fail_booking)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": PATIENT_SUBJECT,
        "realm_access": {"roles": ["patient"]},
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/appointments",
                json={
                    "provider_id": str(PROVIDER_ID),
                    "starts_at": f"{date.today().isoformat()}T10:00:00+00:00",
                    "ends_at": f"{date.today().isoformat()}T10:30:00+00:00",
                    "reason": "Synthetic test appointment",
                },
            )

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
        assert "synthetic-secret" not in response.text
        assert "db.internal.test" not in response.text
        assert response.headers["X-Request-ID"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        db.close()
        engine.dispose()
