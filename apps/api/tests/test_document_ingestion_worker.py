from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.workers import document_ingestion_worker as worker


def test_process_pending_documents_marks_document_ready(monkeypatch) -> None:
    document = SimpleNamespace(
        id=uuid4(),
        object_key="patients/p/note.txt",
        ingestion_status="pending",
        ingestion_error=None,
        indexed_at=None,
        indexed_chunks=0,
    )

    class FakeDB:
        def __init__(self) -> None:
            self.commits = 0
        def scalars(self, query):
            return SimpleNamespace(all=lambda: [document])
        def commit(self) -> None:
            self.commits += 1
        def scalar(self, query):
            return document

    class FakeResponse:
        def read(self) -> bytes:
            return b"hello"
        def close(self) -> None:
            pass
        def release_conn(self) -> None:
            pass

    class FakeClient:
        def get_object(self, bucket, key):
            return FakeResponse()

    db = FakeDB()
    monkeypatch.setattr(worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(worker, "get_storage_client", lambda: FakeClient())
    monkeypatch.setattr(worker, "index_document", lambda *args: 2)

    assert worker.process_pending_documents() == 1
    assert document.ingestion_status == "ready"
    assert document.indexed_chunks == 2
    assert document.indexed_at is not None
    assert isinstance(document.indexed_at, datetime)
    assert document.indexed_at.tzinfo == timezone.utc


def test_process_pending_documents_isolates_failure(monkeypatch) -> None:
    document = SimpleNamespace(
        id=uuid4(),
        object_key="patients/p/note.txt",
        ingestion_status="pending",
        ingestion_error=None,
        indexed_at=None,
        indexed_chunks=0,
    )

    class FakeDB:
        def scalars(self, query):
            return SimpleNamespace(all=lambda: [document])
        def commit(self) -> None:
            pass
        def rollback(self) -> None:
            pass
        def scalar(self, query):
            return document

    db = FakeDB()
    monkeypatch.setattr(worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(worker, "get_storage_client", lambda: (_ for _ in ()).throw(RuntimeError("storage unavailable")))

    assert worker.process_pending_documents() == 0
    assert document.ingestion_status == "failed"
    assert document.indexed_chunks == 0
    assert document.ingestion_error == "storage unavailable"
