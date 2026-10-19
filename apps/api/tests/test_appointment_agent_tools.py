from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.appointment_tools import book_appointment, get_available_slots


def test_book_appointment_requires_timezone() -> None:
    with pytest.raises(ValueError, match="timezone"):
        book_appointment(
            db=None,
            patient_id=uuid4(),
            provider_id=uuid4(),
            starts_at=datetime(2026, 9, 9, 18, 0),
            ends_at=datetime(2026, 9, 9, 18, 30),
        )


def test_book_appointment_rejects_reversed_times() -> None:
    with pytest.raises(ValueError, match="after"):
        book_appointment(
            db=None,
            patient_id=uuid4(),
            provider_id=uuid4(),
            starts_at=datetime(2026, 9, 9, 18, 30, tzinfo=timezone.utc),
            ends_at=datetime(2026, 9, 9, 18, 0, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    ("booked_start", "booked_end", "expected_starts"),
    [
        (time(10, 15), time(10, 45), ["11:00"]),
        (time(9, 30), time(10, 15), ["11:00"]),
        (time(10, 30), time(11, 0), ["10:00", "11:00"]),
    ],
)
def test_available_slots_exclude_any_overlapping_booking(
    booked_start: time, booked_end: time, expected_starts: list[str]
) -> None:
    day = date(2026, 11, 11)
    slots = [
        SimpleNamespace(start_time=time(10), end_time=time(10, 30)),
        SimpleNamespace(start_time=time(11), end_time=time(11, 30)),
    ]
    booked = [
        SimpleNamespace(
            starts_at=datetime.combine(day, booked_start, tzinfo=timezone.utc),
            ends_at=datetime.combine(day, booked_end, tzinfo=timezone.utc),
        )
    ]
    db = MagicMock()
    db.scalars.side_effect = [SimpleNamespace(all=lambda: slots), SimpleNamespace(all=lambda: booked)]

    result = get_available_slots(db, uuid4(), day)

    assert [item["start"][11:16] for item in result] == expected_starts
