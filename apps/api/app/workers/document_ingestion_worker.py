from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.db.session import SessionLocal
from app.models.document import PatientDocument
from app.services.documents import get_storage_client
from app.services.document_ingestion import index_document

logger = logging.getLogger(__name__)
POLL_SECONDS = 10
BATCH_SIZE = 5
MAX_ERROR_LENGTH = 1000


def process_pending_documents(limit: int = BATCH_SIZE) -> int:
    processed = 0
    with SessionLocal() as db:
        documents = db.scalars(
            select(PatientDocument)
            .where(PatientDocument.ingestion_status == "pending")
            .order_by(PatientDocument.created_at)
            .limit(limit)
        ).all()
        for document in documents:
            document.ingestion_status = "processing"
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

                indexed_chunks = index_document(db, document, content) or 0
                document.ingestion_status = "ready"
                document.indexed_at = datetime.now(timezone.utc)
                document.indexed_chunks = indexed_chunks
                document.ingestion_error = None
                db.commit()
                processed += 1
            except Exception as exc:  # noqa: BLE001 - worker must isolate failures per document.
                logger.exception("document ingestion failed document_id=%s", document.id)
                db.rollback()
                failed = db.scalar(select(PatientDocument).where(PatientDocument.id == document.id))
                if failed is not None:
                    failed.ingestion_status = "failed"
                    failed.indexed_at = None
                    failed.indexed_chunks = 0
                    failed.ingestion_error = str(exc)[:MAX_ERROR_LENGTH]
                    db.commit()
    return processed


def run() -> None:
    logger.info("document ingestion worker started")
    while True:
        try:
            processed = process_pending_documents()
            if processed:
                logger.info("processed %s document(s)", processed)
        except Exception:
            logger.exception("document ingestion polling failed")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
