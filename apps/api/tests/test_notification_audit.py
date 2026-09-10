from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.clinical import process_notifications
from app.db.base import Base
from app.models import AuditEvent, Patient

ADMIN_SUBJECT = "admin-notification-test"
PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")


def test_admin_notification_processing_is_audited(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, AuditEvent.__table__])
    db = Session(engine)
    try:
        db.add(
            Patient(
                id=PATIENT_ID,
                external_id=ADMIN_SUBJECT,
                first_name="Notification",
                last_name="Admin",
                email="admin@example.test",
            )
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.notifications.process_pending_notifications",
            lambda session: 3,
        )

        response = process_notifications(
            {"sub": ADMIN_SUBJECT},
            db,
        )

        assert response.processed == 3
        event = db.query(AuditEvent).one()
        assert event.actor_subject == ADMIN_SUBJECT
        assert event.actor_role == "admin"
        assert event.action == "notification.process"
        assert event.resource_type == "notification"
        assert event.resource_id is None
        assert event.metadata_json == {"processed": 3}
        assert event.outcome == "success"
    finally:
        db.close()
        engine.dispose()
