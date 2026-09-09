from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Appointment, Notification, Patient, Provider
from app.models.appointment import AppointmentStatus
from app.models.notification import NotificationStatus, NotificationType
from app.services.notifications import (
    REMINDER_OFFSETS,
    process_pending_notifications,
    schedule_appointment_reminders,
)


PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
PROVIDER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Patient.__table__,
            Provider.__table__,
            Appointment.__table__,
            Notification.__table__,
        ],
    )
    db = Session(engine)
    db.add_all(
        [
            Patient(
                id=PATIENT_ID,
                external_id="notification-patient",
                first_name="Demo",
                last_name="Patient",
                email="patient@example.test",
            ),
            Provider(
                id=PROVIDER_ID,
                external_id="notification-provider",
                first_name="Demo",
                last_name="Provider",
                specialty="Cardiology",
                email="provider@example.test",
            ),
        ]
    )
    db.commit()
    return db


def _appointment(
    db: Session, *, starts_at: datetime, status: str = AppointmentStatus.SCHEDULED
) -> Appointment:
    appointment = Appointment(
        patient_id=PATIENT_ID,
        provider_id=PROVIDER_ID,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        status=status,
        reason="Routine consultation",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


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


def test_scheduling_reminders_is_idempotent() -> None:
    db = _build_session()
    try:
        now = datetime.now(timezone.utc)
        appointment = _appointment(db, starts_at=now + timedelta(hours=30))

        assert schedule_appointment_reminders(db, appointment) == 2
        assert schedule_appointment_reminders(db, appointment) == 0

        notifications = db.scalars(
            select(Notification).where(Notification.appointment_id == appointment.id)
        ).all()
        assert len(notifications) == 2
        assert {item.status for item in notifications} == {NotificationStatus.PENDING}
        assert {item.notification_type for item in notifications} == {
            NotificationType.APPOINTMENT_REMINDER_24H,
            NotificationType.APPOINTMENT_REMINDER_1H,
        }
    finally:
        engine = db.get_bind()
        db.close()
        engine.dispose()


def test_due_reminder_is_sent_once(monkeypatch) -> None:
    db = _build_session()
    try:
        now = datetime.now(timezone.utc)
        appointment = _appointment(db, starts_at=now + timedelta(hours=2))
        schedule_appointment_reminders(db, appointment)
        sent: list[str] = []
        monkeypatch.setattr(
            "app.services.notifications.send_email",
            lambda notification: sent.append(notification.notification_type),
        )

        assert process_pending_notifications(db, now=now + timedelta(hours=1, minutes=1)) == 1
        assert sent == [NotificationType.APPOINTMENT_REMINDER_1H]
        notification = db.scalar(
            select(Notification).where(
                Notification.appointment_id == appointment.id,
                Notification.notification_type == NotificationType.APPOINTMENT_REMINDER_1H,
            )
        )
        assert notification is not None
        assert notification.status == NotificationStatus.SENT

        assert process_pending_notifications(db, now=now + timedelta(hours=1, minutes=2)) == 0
        assert sent == [NotificationType.APPOINTMENT_REMINDER_1H]
    finally:
        engine = db.get_bind()
        db.close()
        engine.dispose()


def test_due_reminder_for_terminal_appointment_is_not_sent(monkeypatch) -> None:
    db = _build_session()
    try:
        now = datetime(2026, 9, 9, 10, 0, tzinfo=timezone.utc)
        appointment = _appointment(
            db,
            starts_at=now + timedelta(hours=2),
            status=AppointmentStatus.CANCELLED,
        )
        notification = Notification(
            appointment_id=appointment.id,
            notification_type=NotificationType.APPOINTMENT_REMINDER_1H,
            channel="email",
            recipient="patient@example.test",
            subject="Reminder",
            body="Reminder",
            scheduled_for=now,
            status=NotificationStatus.PENDING,
        )
        db.add(notification)
        db.commit()
        monkeypatch.setattr(
            "app.services.notifications.send_email",
            lambda _: (_ for _ in ()).throw(AssertionError("cancelled appointment must not send")),
        )

        assert process_pending_notifications(db, now=now + timedelta(minutes=1)) == 1
        db.refresh(notification)
        assert notification.status == NotificationStatus.FAILED
        assert notification.error_message == "Appointment is no longer active"
    finally:
        engine = db.get_bind()
        db.close()
        engine.dispose()
