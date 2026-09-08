from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from app.models.appointment import AppointmentStatus


PATIENT_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a101")
PROVIDER_ID = UUID("7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a102")


def test_demo_identity_ids_are_stable() -> None:
    assert str(PATIENT_ID) == "7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a101"
    assert str(PROVIDER_ID) == "7f7d4cc2-8c35-4e7c-a1e2-5b5d1c01a102"


def test_appointment_status_values_match_api_contract() -> None:
    assert AppointmentStatus.SCHEDULED.value == "scheduled"
    assert AppointmentStatus.CONFIRMED.value == "confirmed"
    assert AppointmentStatus.CANCELLED.value == "cancelled"
    assert AppointmentStatus.COMPLETED.value == "completed"
    assert AppointmentStatus.NO_SHOW.value == "no_show"


def test_demo_availability_is_half_hour_slot() -> None:
    starts_at = datetime.combine(
        datetime(2026, 9, 9).date(), time(10, 0), tzinfo=timezone.utc
    )
    ends_at = datetime.combine(
        datetime(2026, 9, 9).date(), time(10, 30), tzinfo=timezone.utc
    )
    assert ends_at - starts_at == timedelta(minutes=30)
