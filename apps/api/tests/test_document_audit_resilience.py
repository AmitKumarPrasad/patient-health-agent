from uuid import uuid4

from app.api.documents import _record_patient_document_event
from app.models.patient import Patient


class DummyDB:
    def __init__(self) -> None:
        self.rollback_called = False

    def rollback(self) -> None:
        self.rollback_called = True


def test_document_audit_failure_does_not_escape(monkeypatch) -> None:
    db = DummyDB()
    patient = Patient(id=1, first_name="Test", last_name="Patient")

    def fail_audit(db, **kwargs):
        raise RuntimeError("audit database unavailable")

    monkeypatch.setattr("app.api.documents.record_event", fail_audit)

    _record_patient_document_event(
        db,
        subject="demo.patient",
        action="record.delete",
        patient=patient,
        resource_id=str(uuid4()),
    )

    assert db.rollback_called is True
