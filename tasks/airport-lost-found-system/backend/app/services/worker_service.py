from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.utils import run_matching_for_found_item, run_matching_for_lost_report
from app.core.config import get_settings
from app.models import (
    BackgroundJob,
    FoundItem,
    LostReport,
    Notification,
    NotificationChannel,
    NotificationStatus,
    OutboxEvent,
    User,
    WorkStatus,
)
from app.services.notification_service import notification_service
from app.services.notification_template_service import select_template
from app.services.outbox_service import mark_retryable


logger = logging.getLogger(__name__)


class WorkerService:
    LEASE_SECONDS = 60

    def list_due_outbox(self, db: Session, limit: int = 25) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        return (
            db.query(OutboxEvent)
            .filter(
                OutboxEvent.status.in_([WorkStatus.pending, WorkStatus.failed]),
                or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now),
                or_(OutboxEvent.leased_until.is_(None), OutboxEvent.leased_until <= now),
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
                or_(BackgroundJob.leased_until.is_(None), BackgroundJob.leased_until <= now),
            )
            .order_by(BackgroundJob.created_at.asc())
            .limit(limit)
            .all()
        )

    def reap_orphaned(self, db: Session) -> int:
        """Reset rows that crashed mid-processing (lease expired)."""
        now = datetime.now(UTC)
        outbox_reset = (
            db.query(OutboxEvent)
            .filter(OutboxEvent.status == WorkStatus.processing, OutboxEvent.leased_until.isnot(None), OutboxEvent.leased_until <= now)
            .update({"status": WorkStatus.pending}, synchronize_session=False)
        )
        job_reset = (
            db.query(BackgroundJob)
            .filter(BackgroundJob.status == WorkStatus.processing, BackgroundJob.leased_until.isnot(None), BackgroundJob.leased_until <= now)
            .update({"status": WorkStatus.pending}, synchronize_session=False)
        )
        if outbox_reset or job_reset:
            logger.info(
                "reaped orphaned work",
                extra={"event": "worker_reaped", "outbox_count": int(outbox_reset), "job_count": int(job_reset)},
            )
        return int(outbox_reset) + int(job_reset)

    async def process_outbox_once(self, db: Session) -> int:
        processed = 0
        for event in self.list_due_outbox(db):
            event_id = event.id
            try:
                event.status = WorkStatus.processing
                event.leased_until = datetime.now(UTC) + timedelta(seconds=self.LEASE_SECONDS)
                db.flush()
                await self._handle_outbox(db, event)
                event.status = WorkStatus.succeeded
                event.last_error = None
                event.leased_until = None
                processed += 1
            except Exception as exc:
                logger.exception("outbox processing failed", extra={"event": "outbox_failed", "outbox_event_id": event_id})
                db.rollback()
                retry_event = db.get(OutboxEvent, event_id)
                if retry_event:
                    retry_event.leased_until = None
                    mark_retryable(retry_event, str(exc))
        db.commit()
        return processed

    async def process_jobs_once(self, db: Session) -> int:
        processed = 0
        for job in self.list_due_jobs(db):
            job_id = job.id
            try:
                job.status = WorkStatus.processing
                job.leased_until = datetime.now(UTC) + timedelta(seconds=self.LEASE_SECONDS)
                db.flush()
                await self._run_job(db, job)
                job.status = WorkStatus.succeeded
                job.last_error = None
                job.leased_until = None
                processed += 1
            except Exception as exc:
                logger.exception("job processing failed", extra={"event": "job_failed", "job_id": job_id})
                db.rollback()
                retry_job = db.get(BackgroundJob, job_id)
                if retry_job:
                    retry_job.leased_until = None
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
        if job.job_type == "graph.summary.generate":
            # Pre-warm cache for graph context — best-effort, no-op if data is missing.
            from app.services.graph_context_service import graph_context_service

            entity_type = job.payload_json.get("entity_type")
            entity_id = job.payload_json.get("entity_id")
            if entity_type == "lost_report" and entity_id is not None:
                try:
                    await graph_context_service.lost_report_context(db, int(entity_id))
                except ValueError:
                    pass
            elif entity_type == "found_item" and entity_id is not None:
                try:
                    await graph_context_service.found_item_context(db, int(entity_id))
                except ValueError:
                    pass
            return
        logger.warning("unknown job type", extra={"event": "job_unknown_type", "job_type": job.job_type})

    async def _handle_outbox(self, db: Session, event: OutboxEvent) -> None:
        payload = event.payload_json or {}
        if event.event_type == "match_candidate.upserted":
            await self._notify_passenger_about_match(db, payload)
            return
        if event.event_type == "item.released":
            await self._notify_passenger_about_release(db, payload)
            return
        # Other event types are recorded for downstream consumers but do nothing here.

    async def _notify_passenger_about_match(self, db: Session, payload: dict[str, Any]) -> None:
        confidence = (payload.get("confidence_level") or "").lower()
        if confidence != "high":
            return
        report_id = payload.get("lost_report_id")
        if report_id is None:
            return
        report = db.get(LostReport, int(report_id))
        if not report:
            return
        passenger = db.get(User, report.passenger_id) if report.passenger_id else None
        await self._send_notification_for_report(
            db,
            report,
            passenger,
            event_type="match_candidate.upserted",
            event_payload={
                "report_code": report.report_code,
                "confidence_level": confidence,
            },
            match_candidate_id=payload.get("match_candidate_id") or _extract_match_id(payload),
        )

    async def _notify_passenger_about_release(self, db: Session, payload: dict[str, Any]) -> None:
        report_id = payload.get("lost_report_id")
        if report_id is None:
            # The release outbox writes from found_item side — look up the report through the claim.
            from app.models import ClaimVerification

            claim_id = payload.get("claim_verification_id")
            if claim_id is None:
                return
            claim = db.get(ClaimVerification, int(claim_id))
            if not claim:
                return
            report_id = claim.lost_report_id
        report = db.get(LostReport, int(report_id))
        if not report:
            return
        passenger = db.get(User, report.passenger_id) if report.passenger_id else None
        await self._send_notification_for_report(
            db,
            report,
            passenger,
            event_type="item.released",
            event_payload={"report_code": report.report_code},
            match_candidate_id=None,
        )

    async def _send_notification_for_report(
        self,
        db: Session,
        report: LostReport,
        passenger: User | None,
        *,
        event_type: str,
        event_payload: dict[str, Any],
        match_candidate_id: int | None,
    ) -> None:
        language = (passenger.preferred_language if passenger else None) or "en"
        rendered = select_template(event_type, event_payload, language)
        if not rendered:
            return
        subject, body = rendered
        channel_pref = (passenger.preferred_channel if passenger else "email") or "email"
        if channel_pref == "none":
            return
        recipient_email = (passenger.email if passenger else None) or report.contact_email
        recipient_phone = (passenger.phone if passenger else None) or report.contact_phone
        channel: NotificationChannel | None = None
        recipient = None
        if channel_pref == "sms" and recipient_phone:
            channel = NotificationChannel.sms
            recipient = recipient_phone
        elif recipient_email:
            channel = NotificationChannel.email
            recipient = recipient_email
        elif recipient_phone:
            channel = NotificationChannel.sms
            recipient = recipient_phone
        if not channel or not recipient:
            return
        if self._already_notified(db, report.id, event_type, recipient):
            return
        notification = Notification(
            user_id=passenger.id if passenger else None,
            lost_report_id=report.id,
            match_candidate_id=match_candidate_id,
            channel=channel,
            recipient=recipient,
            message=f"{subject}\n\n{body}",
            status=NotificationStatus.pending,
        )
        db.add(notification)
        db.flush()
        try:
            await notification_service.send_notification(db, notification)
        except Exception:
            logger.exception("notification dispatch failed", extra={"event": "notification_send_failed", "lost_report_id": report.id})
            notification.status = NotificationStatus.failed
            db.add(notification)
            db.flush()

    def _already_notified(self, db: Session, report_id: int, event_type: str, recipient: str) -> bool:
        # Throttle: don't double-notify the same recipient for the same event_type within an hour.
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        marker = f"[{event_type}]"
        existing = (
            db.query(Notification.id)
            .filter(
                Notification.lost_report_id == report_id,
                Notification.recipient == recipient,
                Notification.created_at >= cutoff,
                Notification.message.contains(marker[:48]),
            )
            .first()
        )
        return existing is not None


def _extract_match_id(payload: dict[str, Any]) -> int | None:
    value = payload.get("match_candidate_id")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


worker_service = WorkerService()
