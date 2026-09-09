from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.services.documents import upload_document


@pytest.mark.parametrize(
    ("content_type", "content"),
    [
        ("application/pdf", b"%PDF-1.7\ntruncated"),
        ("image/png", b"\x89PNG\r\n\x1a\n"),
        ("image/jpeg", b"\xff\xd8\xff\xd9"),
    ],
)
def test_upload_rejects_signed_but_structurally_invalid_binary(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
    content: bytes,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[Patient.__table__, PatientDocument.__table__],
    )

    def unexpected_storage_access():
        raise AssertionError("invalid content reached object storage")

    monkeypatch.setattr(
        "app.services.documents.get_storage_client", unexpected_storage_access
    )

    with Session(engine) as db:
        patient = Patient(first_name="Test", last_name="Patient")
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with pytest.raises(
            ValueError,
            match="Document structure is invalid|structurally invalid",
        ):
            upload_document(
                db,
                patient,
                filename="invalid.bin",
                content_type=content_type,
                content=content,
                category=None,
                description=None,
            )
