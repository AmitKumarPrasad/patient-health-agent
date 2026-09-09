from uuid import uuid4

from app.agents.appointment_agent import _record_document_search_event


class DummyDB:
    def __init__(self) -> None:
        self.rollback_called = False

    def rollback(self) -> None:
        self.rollback_called = True


def test_document_search_audit_failure_does_not_escape(monkeypatch) -> None:
    db = DummyDB()
    patient_id = uuid4()

    def fail_audit(db, **kwargs):
        raise RuntimeError("audit database unavailable")

    monkeypatch.setattr("app.agents.appointment_agent.record_event", fail_audit)

    _record_document_search_event(
        db,
        subject="demo.patient",
        patient_id=patient_id,
        result_count=3,
    )

    assert db.rollback_called is True
