from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.config import settings
from app.db.session import SessionLocal
from app.models.document import PatientDocument
from app.observability.safe_logging import PHISafeLogFilter, safe_log_exception
from app.services.document_ingestion import index_document
from app.services.documents import get_storage_client

logger = logging.getLogger(__name__)
logger.addFilter(PHISafeLogFilter())
POLL_SECONDS = 10
BATCH_SIZE = 5
MAX_ERROR_LENGTH = 1000
MAX_ATTEMPTS = 5
PROCESSING_TIMEOUT = timedelta(minutes=15)


def _backoff(attempt: int) -> timedelta:
    return timedelta(seconds=min(900, 30 * (2 ** max(0, attempt - 1))))


def process_pending_documents(limit: int = BATCH_SIZE) -> int:
    processed = 0
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        stale_before = now - PROCESSING_TIMEOUT
        candidates = db.scalars(
            select(PatientDocument)
            .where(
                or_(
                    (PatientDocument.ingestion_status == "pending")
                    & (or_(PatientDocument.next_attempt_at.is_(None), PatientDocument.next_attempt_at <= now)),
                    (PatientDocument.ingestion_status == "failed")
                    & (PatientDocument.ingestion_attempts < MAX_ATTEMPTS)
                    & (or_(PatientDocument.next_attempt_at.is_(None), PatientDocument.next_attempt_at <= now)),
                    (PatientDocument.ingestion_status == "processing")
                    & (PatientDocument.processing_started_at < stale_before),
                )
            )
            .order_by(PatientDocument.created_at)
            .with_for_update(skip_locked=True)
            .limit(limit)
        ).all()

        for document in candidates:
            document.ingestion_status = "processing"
            document.processing_started_at = now
            document.ingestion_attempts += 1
            document.ingestion_error = None
            db.commit()
            try:
                client = get_storage_client()
                response = client.get_object(settings.minio_bucket, document.object_key)
                try:
                    content = response.read()
                finally:
                    response.close()
                    response.release_conn()

                if document.sha256 and hashlib.sha256(content).hexdigest() != document.sha256:
                    raise ValueError("Document integrity check failed")

                indexed_chunks = index_document(db, document, content) or 0
                document.ingestion_status = "ready"
                document.indexed_at = datetime.now(timezone.utc)
                document.indexed_chunks = indexed_chunks
                document.ingestion_error = None
                document.next_attempt_at = None
                document.processing_started_at = None
                db.commit()
                processed += 1
            except Exception as exc:  # noqa: BLE001 - isolate failures per document.
                safe_log_exception(logger, "document_ingestion_failed", exc, document_id=document.id)
                db.rollback()
                failed = db.scalar(select(PatientDocument).where(PatientDocument.id == document.id))
                if failed is not None:
                    failed.processing_started_at = None
                    failed.indexed_at = None
                    failed.indexed_chunks = 0
                    failed.ingestion_error = str(exc)[:MAX_ERROR_LENGTH]
                    if failed.ingestion_attempts >= MAX_ATTEMPTS:
                        failed.ingestion_status = "failed"
                        failed.next_attempt_at = None
                    else:
                        failed.ingestion_status = "pending"
                        failed.next_attempt_at = datetime.now(timezone.utc) + _backoff(failed.ingestion_attempts)
                    db.commit()
    return processed


def run() -> None:
    logger.info("document ingestion worker started")
    while True:
        try:
            processed = process_pending_documents()
            if processed:
                logger.info("processed %s document(s)", processed)
        except Exception as exc:  # noqa: BLE001 - keep polling after transient failures.
            safe_log_exception(logger, "document_ingestion_polling_failed", exc)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
