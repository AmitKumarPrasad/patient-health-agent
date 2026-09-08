from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.keycloak import require_roles
from app.db.session import get_db
from app.models.audit import AuditEvent

router = APIRouter(prefix="/api/admin/audit", tags=["admin-audit"])


class AuditResponse(BaseModel):
    id: str
    actor_subject: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None
    patient_id: str | None
    created_at: str
    outcome: str
    metadata: dict | None


@router.get("", response_model=list[AuditResponse])
def list_audit_events(
    limit: int = 100,
    _: dict = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[AuditResponse]:
    limit = max(1, min(limit, 500))
    events = db.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    ).all()
    return [
        AuditResponse(
            id=str(event.id),
            actor_subject=event.actor_subject,
            actor_role=event.actor_role,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            patient_id=str(event.patient_id) if event.patient_id else None,
            created_at=event.created_at.isoformat() if isinstance(event.created_at, datetime) else str(event.created_at),
            outcome=event.outcome,
            metadata=event.metadata_json,
        )
        for event in events
    ]
