from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.services.patient_identity import get_patient_by_external_id, require_patient_by_external_id


def test_patient_identity_is_resolved_from_external_id() -> None:
    engine = create_engine("sqlite:///:memory:")
    Patient.__table__.create(engine)
    patient_id = uuid4()

    with Session(engine) as db:
        db.add(
            Patient(
                id=patient_id,
                external_id="keycloak-sub-123",
                first_name="Demo",
                last_name="Patient",
            )
        )
        db.commit()

        patient = get_patient_by_external_id(db, "keycloak-sub-123")
        assert patient is not None
        assert patient.id == patient_id


def test_unregistered_external_id_is_rejected() -> None:
    engine = create_engine("sqlite:///:memory:")
    Patient.__table__.create(engine)

    with Session(engine) as db:
        with pytest.raises(LookupError, match="not registered"):
            require_patient_by_external_id(db, "missing-sub")
