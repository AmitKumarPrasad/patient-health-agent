from __future__ import annotations

import logging
import time

from app.db.session import SessionLocal
from app.observability.safe_logging import PHISafeLogFilter, safe_log_exception
from app.services.notifications import process_pending_notifications
from app.workers.document_ingestion_worker import process_pending_documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logger.addFilter(PHISafeLogFilter())
POLL_SECONDS = 10


def run() -> None:
    logger.info("background worker started")
    while True:
        db = SessionLocal()
        try:
            processed_notifications = process_pending_notifications(db)
            if processed_notifications:
                logger.info("processed %s notification(s)", processed_notifications)
        except Exception as exc:  # noqa: BLE001 - keep worker alive after transient failures.
            safe_log_exception(logger, "notification_processing_failed", exc)
        finally:
            db.close()

        try:
            processed_documents = process_pending_documents()
            if processed_documents:
                logger.info("processed %s document(s)", processed_documents)
        except Exception as exc:  # noqa: BLE001 - keep worker alive after transient failures.
            safe_log_exception(logger, "document_ingestion_processing_failed", exc)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()
