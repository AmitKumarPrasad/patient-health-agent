from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.documents import get_patient_document
from app.models.patient import Patient


def _patient() -> Patient:
    return Patient(id=1, first_name="Test", last_name="Patient")


def test_missing_document_read_is_audited(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid4()
    events: list[dict] = []

    monkeypatch.setattr("app.api.documents._patient_for_subject", lambda db, subject: _patient())
    monkeypatch.setattr(
        "app.api.documents.download_document",
        lambda db, patient, requested_id: (_ for _ in ()).throw(LookupError("Document not found")),
    )
    monkeypatch.setattr("app.api.documents.record_event", lambda db, **kwargs: events.append(kwargs))

    with pytest.raises(HTTPException) as exc_info:
        get_patient_document(document_id, {"sub": "demo.patient"}, None)

    assert exc_info.value.status_code == 404
    assert events == [
        {
            "actor_subject": "demo.patient",
            "actor_role": "patient",
            "action": "record.read",
            "resource_type": "patient_document",
            "resource_id": str(document_id),
            "patient_id": 1,
            "metadata": None,
            "outcome": "failure",
            "error_message": "Document not found",
        }
    ]


def test_document_storage_failure_is_audited_without_masking_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid4()
    events: list[dict] = []

    monkeypatch.setattr("app.api.documents._patient_for_subject", lambda db, subject: _patient())
    monkeypatch.setattr(
        "app.api.documents.download_document",
        lambda db, patient, requested_id: (_ for _ in ()).throw(RuntimeError("storage backend unavailable")),
    )
    monkeypatch.setattr("app.api.documents.record_event", lambda db, **kwargs: events.append(kwargs))

    with pytest.raises(HTTPException) as exc_info:
        get_patient_document(document_id, {"sub": "demo.patient"}, None)

    assert exc_info.value.status_code == 503
    assert str(exc_info.value.detail) == "storage backend unavailable"
    assert events[0]["resource_id"] == str(document_id)
    assert events[0]["outcome"] == "failure"
    assert events[0]["error_message"] == "Document retrieval failed"


def test_document_read_preserves_http_error_when_audit_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid4()

    monkeypatch.setattr("app.api.documents._patient_for_subject", lambda db, subject: _patient())
    monkeypatch.setattr(
        "app.api.documents.download_document",
        lambda db, patient, requested_id: (_ for _ in ()).throw(LookupError("Document not found")),
    )

    def fail_audit(db, **kwargs):
        raise RuntimeError("audit database unavailable")

    monkeypatch.setattr("app.api.documents.record_event", fail_audit)

    with pytest.raises(HTTPException) as exc_info:
        get_patient_document(document_id, {"sub": "demo.patient"}, None)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found"
