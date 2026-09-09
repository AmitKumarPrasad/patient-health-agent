import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.services.documents import get_document


def test_patient_cannot_access_another_patients_document() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, PatientDocument.__table__])

    with Session(engine) as db:
        patient_a = Patient(first_name="Patient", last_name="A")
        patient_b = Patient(first_name="Patient", last_name="B")
        db.add_all([patient_a, patient_b])
        db.flush()

        document = PatientDocument(
            patient_id=patient_a.id,
            object_key="patients/a/private/note.txt",
            original_filename="note.txt",
            content_type="text/plain",
            size_bytes=5,
            sha256="abc123",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        assert get_document(db, patient_a, document.id) is document
        with pytest.raises(LookupError, match="Document not found"):
            get_document(db, patient_b, document.id)
