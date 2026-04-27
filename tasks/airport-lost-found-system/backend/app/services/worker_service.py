from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import BackgroundJob, OutboxEvent, WorkStatus
from app.services.outbox_service import mark_retryable


class WorkerService:
    def list_due_outbox(self, db: Session, limit: int = 25) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        return (
            db.query(OutboxEvent)
            .filter(
                OutboxEvent.status.in_([WorkStatus.pending, WorkStatus.failed]),
                or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now),
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .all()
        )

    def list_due_jobs(self, db: Session, limit: int = 25) -> list[BackgroundJob]:
        now = datetime.now(UTC)
        return (
            db.query(BackgroundJob)
            .filter(
                BackgroundJob.status.in_([WorkStatus.pending, WorkStatus.failed]),
                or_(BackgroundJob.next_run_at.is_(None), BackgroundJob.next_run_at <= now),
            )
            .order_by(BackgroundJob.created_at.asc())
            .limit(limit)
            .all()
        )

    def process_outbox_once(self, db: Session) -> int:
        processed = 0
        for event in self.list_due_outbox(db):
            try:
                event.status = WorkStatus.processing
                db.flush()
                # Pilot worker: concrete Azure adapters are already called inline today.
                # This durable outbox gives us retry/dead-letter plumbing for the next step.
                event.status = WorkStatus.succeeded
                event.last_error = None
                processed += 1
            except Exception as exc:
                mark_retryable(event, str(exc))
        db.commit()
        return processed

    def process_jobs_once(self, db: Session) -> int:
        processed = 0
        for job in self.list_due_jobs(db):
            try:
                job.status = WorkStatus.processing
                db.flush()
                job.status = WorkStatus.succeeded
                job.last_error = None
                processed += 1
            except Exception as exc:
                mark_retryable(job, str(exc))
        db.commit()
        return processed


worker_service = WorkerService()
