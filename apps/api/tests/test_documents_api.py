from uuid import uuid4

from sqlalchemy.orm import Session

from app.api.documents import get_patient_document
from app.models.document import PatientDocument
from app.models.patient import Patient


def test_patient_document_download_prevents_caching(monkeypatch) -> None:
    document_id = uuid4()
    document = PatientDocument(
        patient_id=1,
        object_key="patients/1/demo/report.txt",
        original_filename="report.txt",
        content_type="text/plain",
        size_bytes=7,
        sha256=None,
    )
    monkeypatch.setattr(
        "app.api.documents._patient_for_subject",
        lambda db, subject: Patient(id=1, first_name="Test", last_name="Patient"),
    )
    monkeypatch.setattr(
        "app.api.documents.download_document",
        lambda db, patient, requested_id: (document, b"patient-data"),
    )

    response = get_patient_document(document_id, {"sub": "synthetic-patient"}, Session())

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-type"] == "text/plain"
    assert 'attachment; filename="report.txt"' == response.headers["content-disposition"]
    assert response.body == b"patient-data"
