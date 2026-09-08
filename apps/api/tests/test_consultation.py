from uuid import UUID

from app.services.consultation import consultation_url


APPOINTMENT_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a301")


def test_consultation_url_strips_trailing_slash() -> None:
    assert (
        consultation_url("http://localhost:8443/", "patient-health-room")
        == "http://localhost:8443/patient-health-room"
    )


def test_room_names_remain_appointment_scoped() -> None:
    first = consultation_url("https://meet.example.test", f"patient-health-{APPOINTMENT_ID}")
    second = consultation_url(
        "https://meet.example.test", "patient-health-7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a302"
    )
    assert first != second
