from __future__ import annotations

import logging
import asyncio
import time

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.observability import setup_logging
from app.services.worker_service import worker_service


logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    settings = get_settings()
    logger.info("worker started", extra={"event": "worker_started"})
    while True:
        db = SessionLocal()
        try:
            outbox_count = worker_service.process_outbox_once(db)
            job_count = asyncio.run(worker_service.process_jobs_once(db))
            if outbox_count or job_count:
                logger.info(
                    "worker processed work",
                    extra={"event": "worker_processed", "outbox_count": outbox_count, "job_count": job_count},
                )
        except Exception:
            logger.exception("worker loop failed", extra={"event": "worker_failed"})
        finally:
            db.close()
        time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
