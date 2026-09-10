from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.audit import list_audit_events
from app.auth.keycloak import require_roles
from app.db.base import Base
from app.models import AuditEvent, Patient


PATIENT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_PATIENT_ID = UUID("33333333-3333-3333-3333-333333333333")


def _build_database() -> tuple[object, Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, AuditEvent.__table__])
    db = Session(engine)
    db.add_all(
        [
            Patient(
                id=PATIENT_ID,
                external_id="audit-patient",
                first_name="Audit",
                last_name="Patient",
                email="audit@example.test",
            ),
            Patient(
                id=OTHER_PATIENT_ID,
                external_id="audit-other",
                first_name="Other",
                last_name="Patient",
                email="other@example.test",
            ),
        ]
    )
    base_time = datetime(2026, 9, 10, 8, 0, tzinfo=timezone.utc)
    db.add_all(
        [
            AuditEvent(
                id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                actor_subject="provider-1",
                actor_role="provider",
                action="appointment.status_change",
                resource_type="appointment",
                resource_id="appointment-1",
                patient_id=PATIENT_ID,
                metadata_json={"from_status": "scheduled", "to_status": "confirmed"},
                created_at=base_time,
            ),
            AuditEvent(
                id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                actor_subject="provider-2",
                actor_role="provider",
                action="appointment.status_change",
                resource_type="appointment",
                resource_id="appointment-2",
                patient_id=OTHER_PATIENT_ID,
                metadata_json={"from_status": "confirmed", "to_status": "completed"},
                created_at=base_time.replace(hour=9),
            ),
            AuditEvent(
                id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                actor_subject="patient-1",
                actor_role="patient",
                action="document.search",
                resource_type="document",
                resource_id="document-1",
                patient_id=PATIENT_ID,
                metadata_json={"query_length": 12},
                created_at=base_time.replace(hour=10),
                outcome="success",
            ),
        ]
    )
    db.commit()
    return engine, db


def test_admin_audit_history_is_newest_first_and_paginated() -> None:
    engine, db = _build_database()
    try:
        page = list_audit_events(
            limit=2,
            offset=0,
            patient_id=None,
            actor_subject=None,
            action=None,
            resource_type=None,
            resource_id=None,
            outcome=None,
            _={},
            db=db,
        )
        assert [item.id for item in page] == [
            "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        ]

        second_page = list_audit_events(
            limit=2,
            offset=2,
            patient_id=None,
            actor_subject=None,
            action=None,
            resource_type=None,
            resource_id=None,
            outcome=None,
            _={},
            db=db,
        )
        assert [item.id for item in second_page] == ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]
    finally:
        db.close()
        engine.dispose()


def test_admin_audit_history_filters_by_patient_and_action() -> None:
    engine, db = _build_database()
    try:
        events = list_audit_events(
            limit=100,
            offset=0,
            patient_id=PATIENT_ID,
            actor_subject=None,
            action="appointment.status_change",
            resource_type=None,
            resource_id=None,
            outcome=None,
            _={},
            db=db,
        )
        assert len(events) == 1
        assert events[0].resource_id == "appointment-1"
        assert events[0].metadata == {"from_status": "scheduled", "to_status": "confirmed"}
    finally:
        db.close()
        engine.dispose()


def test_admin_audit_history_filters_exact_actor_and_resource() -> None:
    engine, db = _build_database()
    try:
        events = list_audit_events(
            limit=100,
            offset=0,
            patient_id=None,
            actor_subject="provider-2",
            action=None,
            resource_type="appointment",
            resource_id="appointment-2",
            outcome="success",
            _={},
            db=db,
        )
        assert len(events) == 1
        assert events[0].actor_subject == "provider-2"
        assert events[0].patient_id == str(OTHER_PATIENT_ID)
    finally:
        db.close()
        engine.dispose()


def test_admin_audit_dependency_rejects_non_admin_role() -> None:
    dependency = require_roles("admin")

    with pytest.raises(HTTPException) as exc_info:
        dependency({"sub": "patient-1", "realm_access": {"roles": ["patient"]}})

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient role"


def test_admin_audit_dependency_accepts_realm_admin_role() -> None:
    dependency = require_roles("admin")

    user = dependency({"sub": "admin-1", "realm_access": {"roles": ["admin"]}})

    assert user["sub"] == "admin-1"


def test_admin_audit_dependency_accepts_client_admin_role() -> None:
    dependency = require_roles("admin")

    user = dependency(
        {
            "sub": "admin-2",
            "realm_access": {"roles": []},
            "resource_access": {"patient-health-agent": {"roles": ["admin"]}},
        }
    )

    assert user["sub"] == "admin-2"
