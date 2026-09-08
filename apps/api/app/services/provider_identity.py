from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.provider import Provider


def get_provider_by_external_id(db: Session, external_id: str) -> Provider | None:
    external_id = external_id.strip()
    if not external_id:
        raise ValueError("External identity is required")
    return db.scalar(select(Provider).where(Provider.external_id == external_id))


def require_provider_by_external_id(db: Session, external_id: str) -> Provider:
    provider = get_provider_by_external_id(db, external_id)
    if provider is None:
        raise LookupError("Authenticated provider is not registered")
    return provider
