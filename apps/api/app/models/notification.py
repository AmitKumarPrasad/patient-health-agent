from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationChannel(StrEnum):
    EMAIL = "email"


class NotificationType(StrEnum):
    APPOINTMENT_REMINDER_24H = "appointment_reminder_24h"
    APPOINTMENT_REMINDER_1H = "appointment_reminder_1h"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "appointment_id",
            "notification_type",
            "channel",
            name="uq_notification_appointment_type_channel",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    appointment_id: Mapped[UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    notification_type: Mapped[str] = mapped_column(String(50), index=True)
    channel: Mapped[str] = mapped_column(String(20))
    recipient: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(
            NotificationStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
        ),
        default=NotificationStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    appointment: Mapped["Appointment"] = relationship()
