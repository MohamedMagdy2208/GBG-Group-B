from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import BackgroundJob, FoundItem, LostReport, OutboxEvent, WorkStatus
from app.api.utils import run_matching_for_found_item, run_matching_for_lost_report
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
            event_id = event.id
            try:
                event.status = WorkStatus.processing
                db.flush()
                # Pilot worker: concrete Azure adapters are already called inline today.
                # This durable outbox gives us retry/dead-letter plumbing for the next step.
                event.status = WorkStatus.succeeded
                event.last_error = None
                processed += 1
            except Exception as exc:
                db.rollback()
                retry_event = db.get(OutboxEvent, event_id)
                if retry_event:
                    mark_retryable(retry_event, str(exc))
        db.commit()
        return processed

    async def process_jobs_once(self, db: Session) -> int:
        processed = 0
        for job in self.list_due_jobs(db):
            job_id = job.id
            try:
                job.status = WorkStatus.processing
                db.flush()
                await self._run_job(db, job)
                job.status = WorkStatus.succeeded
                job.last_error = None
                processed += 1
            except Exception as exc:
                db.rollback()
                retry_job = db.get(BackgroundJob, job_id)
                if retry_job:
                    mark_retryable(retry_job, str(exc))
        db.commit()
        return processed

    async def _run_job(self, db: Session, job: BackgroundJob) -> None:
        if job.job_type == "matching.found_item":
            item = db.get(FoundItem, job.payload_json.get("found_item_id"))
            if item:
                await run_matching_for_found_item(db, item)
            return
        if job.job_type == "matching.lost_report":
            report = db.get(LostReport, job.payload_json.get("lost_report_id"))
            if report:
                await run_matching_for_lost_report(db, report)
            return


worker_service = WorkerService()
