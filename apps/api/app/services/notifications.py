from __future__ import annotations

import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.models.patient import Patient
from app.models.provider import Provider


REMINDER_OFFSETS = {
    NotificationType.APPOINTMENT_REMINDER_24H: timedelta(hours=24),
    NotificationType.APPOINTMENT_REMINDER_1H: timedelta(hours=1),
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _reminder_text(
    appointment: Appointment,
    patient: Patient,
    provider: Provider,
    reminder: str,
) -> tuple[str, str]:
    subject = f"Appointment reminder: {provider.first_name} {provider.last_name}"
    body = (
        f"Hello {patient.first_name},\n\n"
        f"This is a reminder for your {provider.specialty} appointment with "
        f"Dr. {provider.first_name} {provider.last_name}.\n\n"
        f"Date/time: {_as_utc(appointment.starts_at).isoformat()}\n"
        f"Reminder: {reminder}\n"
        f"Status: {appointment.status}\n\n"
        "This is an automated message from the Patient Health Agent demo."
    )
    return subject, body


def schedule_appointment_reminders(db: Session, appointment: Appointment) -> int:
    if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        return 0
    patient = db.get(Patient, appointment.patient_id)
    provider = db.get(Provider, appointment.provider_id)
    if patient is None or provider is None or not patient.email:
        return 0

    created = 0
    now = datetime.now(timezone.utc)
    appointment_start = _as_utc(appointment.starts_at)
    for notification_type, offset in REMINDER_OFFSETS.items():
        scheduled_for = appointment_start - offset
        if scheduled_for <= now:
            continue
        exists = db.scalar(
            select(Notification).where(
                Notification.appointment_id == appointment.id,
                Notification.notification_type == notification_type,
                Notification.channel == NotificationChannel.EMAIL,
            )
        )
        if exists is not None:
            continue
        subject, body = _reminder_text(
            appointment,
            patient,
            provider,
            "24 hours before"
            if notification_type == NotificationType.APPOINTMENT_REMINDER_24H
            else "1 hour before",
        )
        db.add(
            Notification(
                appointment_id=appointment.id,
                notification_type=notification_type,
                channel=NotificationChannel.EMAIL,
                recipient=patient.email,
                subject=subject,
                body=body,
                scheduled_for=scheduled_for,
                status=NotificationStatus.PENDING,
            )
        )
        created += 1
    if created:
        db.commit()
    return created


def cancel_pending_appointment_reminders(db: Session, appointment_id: UUID) -> int:
    result = db.execute(
        update(Notification)
        .where(
            Notification.appointment_id == appointment_id,
            Notification.status == NotificationStatus.PENDING,
        )
        .values(status=NotificationStatus.FAILED, error_message="Appointment is no longer active")
    )
    db.commit()
    return result.rowcount


def send_email(notification: Notification) -> None:
    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST is not configured")
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = notification.recipient
    message["Subject"] = notification.subject
    message.set_content(notification.body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        client.send_message(message)


def process_pending_notifications(
    db: Session, *, now: datetime | None = None, limit: int = 50
) -> int:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    notifications = db.scalars(
        select(Notification)
        .where(
            Notification.status == NotificationStatus.PENDING,
            Notification.scheduled_for <= current_time,
        )
        .order_by(Notification.scheduled_for)
        .limit(limit)
    ).all()

    processed = 0
    for notification in notifications:
        try:
            appointment = db.get(Appointment, notification.appointment_id)
            if appointment is None or appointment.status in (
                AppointmentStatus.CANCELLED,
                AppointmentStatus.COMPLETED,
                AppointmentStatus.NO_SHOW,
            ):
                notification.status = NotificationStatus.FAILED
                notification.error_message = "Appointment is no longer active"
            else:
                send_email(notification)
                notification.status = NotificationStatus.SENT
                notification.sent_at = current_time
                notification.error_message = None
        except Exception as exc:  # noqa: BLE001 - persist delivery failure for operator visibility.
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(exc)[:2000]
        processed += 1
    if processed:
        db.commit()
    return processed
