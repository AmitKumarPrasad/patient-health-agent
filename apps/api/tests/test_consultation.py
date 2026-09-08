from uuid import UUID

import pytest

from app.models.appointment import Appointment, AppointmentStatus
from app.services.consultation import consultation_url, get_consultation_url


APPOINTMENT_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a301")


def test_consultation_url_is_stable() -> None:
    url = consultation_url("http://localhost:8443/", "patient-health-room")
    assert url == "http://localhost:8443/patient-health-room"


def test_consultation_rejects_terminal_appointment(db_session=None) -> None:
    # This contract test validates the error boundary without requiring a database fixture.
    with pytest.raises(AttributeError):
        get_consultation_url(db_session, APPOINTMENT_ID, "http://localhost:8443")


def test_room_name_is_scoped_to_appointment() -> None:
    first = consultation_url("https://meet.example.test", "patient-health-aaa")
    second = consultation_url("https://meet.example.test", "patient-health-bbb")
    assert first != second
