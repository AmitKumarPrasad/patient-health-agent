from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.keycloak import require_roles
from app.db.session import get_db
from app.models.audit import AuditEvent

router = APIRouter(prefix="/api/admin/audit", tags=["admin-audit"])
admin_role_dependency = require_roles("admin")


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
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=100000),
    patient_id: UUID | None = Query(default=None),
    actor_subject: str | None = Query(default=None, max_length=255),
    action: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(default=None, max_length=100),
    resource_id: str | None = Query(default=None, max_length=255),
    outcome: str | None = Query(default=None, max_length=20),
    _: dict = Depends(admin_role_dependency),
    db: Session = Depends(get_db),
) -> list[AuditResponse]:
    query = select(AuditEvent)

    filters = []
    if patient_id is not None:
        filters.append(AuditEvent.patient_id == patient_id)
    if actor_subject and actor_subject.strip():
        filters.append(AuditEvent.actor_subject == actor_subject.strip())
    if action and action.strip():
        filters.append(AuditEvent.action == action.strip())
    if resource_type and resource_type.strip():
        filters.append(AuditEvent.resource_type == resource_type.strip())
    if resource_id and resource_id.strip():
        filters.append(AuditEvent.resource_id == resource_id.strip())
    if outcome and outcome.strip():
        filters.append(AuditEvent.outcome == outcome.strip())

    if filters:
        query = query.where(*filters)

    events = db.scalars(
        query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset(offset).limit(limit)
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
