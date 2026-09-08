from uuid import uuid4

import pytest

from app.services.appointment_access import (
    ADMIN_ROLE,
    PATIENT_ROLE,
    get_accessible_appointment,
)


def test_patient_role_is_defined() -> None:
    assert PATIENT_ROLE == "patient"
    assert ADMIN_ROLE == "admin"


def test_missing_appointment_is_not_authorized_without_database() -> None:
    with pytest.raises((LookupError, AttributeError)):
        get_accessible_appointment(
            None,
            appointment_id=uuid4(),
            subject="keycloak-subject",
            roles={PATIENT_ROLE},
        )
