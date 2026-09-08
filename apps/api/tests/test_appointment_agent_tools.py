from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.appointment_tools import book_appointment


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
