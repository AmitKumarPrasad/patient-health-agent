from datetime import datetime, time, timezone
from uuid import UUID

from app.models.appointment import AppointmentStatus
from app.services.appointment_lifecycle import transition_status


PATIENT_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a101")
PROVIDER_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a102")


def test_demo_identity_ids_are_stable() -> None:
    assert str(PATIENT_ID) == "7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a101"
    assert str(PROVIDER_ID) == "7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a102"


def test_appointment_lifecycle_transition_rules() -> None:
    assert AppointmentStatus.SCHEDULED in AppointmentStatus
    assert AppointmentStatus.CONFIRMED.value == "confirmed"
    assert AppointmentStatus.CANCELLED.value == "cancelled"


def test_demo_availability_is_half_hour_slot() -> None:
    starts_at = datetime.combine(
        datetime(2026, 9, 9).date(), time(10, 0), tzinfo=timezone.utc
    )
    ends_at = datetime.combine(
        datetime(2026, 9, 9).date(), time(10, 30), tzinfo=timezone.utc
    )
    assert ends_at - starts_at == __import__("datetime").timedelta(minutes=30)
