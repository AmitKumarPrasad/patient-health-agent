from __future__ import annotations

import logging
import time

from app.db.session import SessionLocal
from app.services.notifications import process_pending_notifications


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    logger.info("notification worker started")
    while True:
        db = SessionLocal()
        try:
            processed = process_pending_notifications(db)
            if processed:
                logger.info("processed %s notification(s)", processed)
        except Exception:
            logger.exception("notification processing failed")
        finally:
            db.close()
        time.sleep(30)


if __name__ == "__main__":
    run()
