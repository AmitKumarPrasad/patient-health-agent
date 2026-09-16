from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.workers import document_ingestion_worker as worker


def _document():
    return SimpleNamespace(id=uuid4(), object_key="patients/p/note.txt", ingestion_status="pending", ingestion_error=None, ingestion_attempts=0, next_attempt_at=None, processing_started_at=None, indexed_at=None, indexed_chunks=0, sha256=None)


def test_process_pending_documents_marks_document_ready(monkeypatch) -> None:
    document = _document()
    class FakeDB:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def scalars(self, query): return SimpleNamespace(all=lambda: [document])
        def commit(self): pass
        def scalar(self, query): return document
    class FakeResponse:
        def read(self): return b"hello"
        def close(self): pass
        def release_conn(self): pass
    class FakeClient:
        def get_object(self, bucket, key): return FakeResponse()
    db = FakeDB()
    monkeypatch.setattr(worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(worker, "get_storage_client", lambda: FakeClient())
    monkeypatch.setattr(worker, "index_document", lambda *args: 2)
    assert worker.process_pending_documents() == 1
    assert document.ingestion_status == "ready"
    assert document.ingestion_attempts == 1
    assert document.indexed_chunks == 2
    assert isinstance(document.indexed_at, datetime)
    assert document.indexed_at.tzinfo == timezone.utc
    assert document.processing_started_at is None
    assert document.next_attempt_at is None


def test_process_pending_documents_retries_failure(monkeypatch) -> None:
    document = _document()
    class FakeDB:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def scalars(self, query): return SimpleNamespace(all=lambda: [document])
        def commit(self): pass
        def rollback(self): pass
        def scalar(self, query): return document
    db = FakeDB()
    monkeypatch.setattr(worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(worker, "get_storage_client", lambda: (_ for _ in ()).throw(RuntimeError("storage unavailable")))
    assert worker.process_pending_documents() == 0
    assert document.ingestion_status == "pending"
    assert document.ingestion_attempts == 1
    assert document.next_attempt_at is not None
    assert document.ingestion_error == "storage unavailable"


def test_process_pending_documents_stops_after_max_attempts(monkeypatch) -> None:
    document = _document()
    document.ingestion_attempts = worker.MAX_ATTEMPTS - 1
    class FakeDB:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def scalars(self, query): return SimpleNamespace(all=lambda: [document])
        def commit(self): pass
        def rollback(self): pass
        def scalar(self, query): return document
    db = FakeDB()
    monkeypatch.setattr(worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(worker, "get_storage_client", lambda: (_ for _ in ()).throw(RuntimeError("storage unavailable")))
    assert worker.process_pending_documents() == 0
    assert document.ingestion_status == "failed"
    assert document.ingestion_attempts == worker.MAX_ATTEMPTS
    assert document.next_attempt_at is None
