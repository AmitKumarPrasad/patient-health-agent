import hashlib
from io import BytesIO

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.document import PatientDocument
from app.models.patient import Patient
from app.services.documents import (
    ALLOWED_CONTENT_TYPES,
    MAX_DOCUMENT_BYTES,
    _safe_filename,
    _validate_content_signature,
    download_document,
    upload_document,
)


def test_safe_filename_strips_path_and_unsafe_characters() -> None:
    assert _safe_filename("../../report<>.pdf") == "report__.pdf"


def test_document_policy_allows_demo_types_and_caps_size() -> None:
    assert "application/pdf" in ALLOWED_CONTENT_TYPES
    assert "image/png" in ALLOWED_CONTENT_TYPES
    assert MAX_DOCUMENT_BYTES == 10 * 1024 * 1024


def test_content_signature_matches_allowed_binary_types() -> None:
    _validate_content_signature("application/pdf", b"%PDF-1.7\n")
    _validate_content_signature("image/png", b"\x89PNG\r\n\x1a\n")
    _validate_content_signature("image/jpeg", b"\xff\xd8\xff\xe0")
    _validate_content_signature("text/plain", b"hello")


@pytest.mark.parametrize(
    ("content_type", "content"),
    [
        ("application/pdf", b"not a pdf"),
        ("image/png", b"not a png"),
        ("image/jpeg", b"not a jpeg"),
    ],
)
def test_content_signature_rejects_mismatched_binary_type(
    content_type: str, content: bytes
) -> None:
    with pytest.raises(ValueError, match="does not match its declared type"):
        _validate_content_signature(content_type, content)


def test_upload_document_stores_sha256(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, PatientDocument.__table__])

    class FakeMinio:
        def bucket_exists(self, bucket: str) -> bool:
            return True

        def put_object(self, bucket: str, key: str, stream: BytesIO, *, length: int, content_type: str) -> None:
            assert stream.read() == b"hello"
            assert length == 5
            assert content_type == "text/plain"

    monkeypatch.setattr("app.services.documents.get_storage_client", lambda: FakeMinio())
    monkeypatch.setattr("app.services.documents.index_document", lambda *args: None)

    with Session(engine) as db:
        patient = Patient(first_name="Test", last_name="Patient")
        db.add(patient)
        db.commit()
        db.refresh(patient)

        document = upload_document(
            db,
            patient,
            filename="note.txt",
            content_type="text/plain",
            content=b"hello",
            category=None,
            description=None,
        )

        assert document.sha256 == hashlib.sha256(b"hello").hexdigest()
        assert document.size_bytes == 5


def test_upload_document_rejects_mismatched_binary_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, PatientDocument.__table__])

    with Session(engine) as db:
        patient = Patient(first_name="Test", last_name="Patient")
        db.add(patient)
        db.commit()
        db.refresh(patient)

        with pytest.raises(ValueError, match="does not match its declared type"):
            upload_document(
                db,
                patient,
                filename="fake.pdf",
                content_type="application/pdf",
                content=b"plain text pretending to be pdf",
                category=None,
                description=None,
            )

    monkeypatch.setattr("app.services.documents.get_storage_client", lambda: None)


def test_upload_document_cleans_up_object_when_db_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, PatientDocument.__table__])

    class FakeMinio:
        def __init__(self) -> None:
            self.put_keys: list[str] = []
            self.removed_keys: list[str] = []

        def bucket_exists(self, bucket: str) -> bool:
            return True

        def put_object(self, bucket: str, key: str, stream: BytesIO, *, length: int, content_type: str) -> None:
            self.put_keys.append(key)
            assert stream.read() == b"hello"
            assert length == 5
            assert content_type == "text/plain"

        def remove_object(self, bucket: str, key: str) -> None:
            self.removed_keys.append(key)

    storage = FakeMinio()
    monkeypatch.setattr("app.services.documents.get_storage_client", lambda: storage)
    monkeypatch.setattr("app.services.documents.index_document", lambda *args: None)

    with Session(engine) as db:
        patient = Patient(first_name="Test", last_name="Patient")
        db.add(patient)
        db.commit()
        db.refresh(patient)

        def fail_commit() -> None:
            raise RuntimeError("database unavailable")

        monkeypatch.setattr(db, "commit", fail_commit)

        with pytest.raises(RuntimeError, match="database unavailable"):
            upload_document(
                db,
                patient,
                filename="note.txt",
                content_type="text/plain",
                content=b"hello",
                category=None,
                description=None,
            )

    assert len(storage.put_keys) == 1
    assert storage.removed_keys == storage.put_keys


def test_download_document_rejects_tampered_content(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Patient.__table__, PatientDocument.__table__])

    class FakeResponse:
        def read(self) -> bytes:
            return b"tampered"

        def close(self) -> None:
            pass

        def release_conn(self) -> None:
            pass

    class FakeMinio:
        def get_object(self, bucket: str, key: str) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr("app.services.documents.get_storage_client", lambda: FakeMinio())

    with Session(engine) as db:
        patient = Patient(first_name="Test", last_name="Patient")
        db.add(patient)
        db.flush()
        document = PatientDocument(
            patient_id=patient.id,
            object_key="patients/test/note.txt",
            original_filename="note.txt",
            content_type="text/plain",
            size_bytes=5,
            sha256=hashlib.sha256(b"hello").hexdigest(),
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        with pytest.raises(RuntimeError, match="integrity check failed"):
            download_document(db, patient, document.id)
