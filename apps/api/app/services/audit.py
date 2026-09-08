from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def record_event(
    db: Session,
    *,
    actor_subject: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    patient_id: UUID | None = None,
    metadata: dict | None = None,
    outcome: str = "success",
    error_message: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_subject=actor_subject,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        patient_id=patient_id,
        metadata_json=metadata,
        outcome=outcome,
        error_message=error_message,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
