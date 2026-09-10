from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_patient_created_at", "patient_id", "created_at"),
        Index("ix_audit_events_actor_created_at", "actor_subject", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_subject: Mapped[str] = mapped_column(String(255), index=True)
    actor_role: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(255))
    patient_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), index=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    outcome: Mapped[str] = mapped_column(String(20), default="success")
    error_message: Mapped[str | None] = mapped_column(Text)
