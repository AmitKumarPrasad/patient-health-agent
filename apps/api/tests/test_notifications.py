from datetime import datetime, timedelta, timezone

from app.models.notification import NotificationType
from app.services.notifications import REMINDER_OFFSETS


def test_reminder_policy_has_24h_and_1h_offsets() -> None:
    assert REMINDER_OFFSETS[NotificationType.APPOINTMENT_REMINDER_24H] == timedelta(hours=24)
    assert REMINDER_OFFSETS[NotificationType.APPOINTMENT_REMINDER_1H] == timedelta(hours=1)


def test_future_reminder_time_is_derived_from_appointment_time() -> None:
    starts_at = datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc)
    assert starts_at - REMINDER_OFFSETS[NotificationType.APPOINTMENT_REMINDER_24H] == datetime(
        2026, 9, 11, 10, 0, tzinfo=timezone.utc
    )
    assert starts_at - REMINDER_OFFSETS[NotificationType.APPOINTMENT_REMINDER_1H] == datetime(
        2026, 9, 12, 9, 0, tzinfo=timezone.utc
    )
