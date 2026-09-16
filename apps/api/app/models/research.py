from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchSession(Base):
    __tablename__ = "research_sessions"
    __table_args__ = (
        Index("ix_research_sessions_owner_updated_at", "owner_subject", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_subject: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New research session")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    messages: Mapped[list[ResearchMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ResearchMessage.created_at"
    )


class ResearchMessage(Base):
    __tablename__ = "research_messages"
    __table_args__ = (
        Index("ix_research_messages_session_created_at", "session_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict] | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    session: Mapped[ResearchSession] = relationship(back_populates="messages")
