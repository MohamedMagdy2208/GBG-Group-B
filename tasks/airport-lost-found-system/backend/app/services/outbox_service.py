from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BackgroundJob, OutboxEvent, WorkStatus


def enqueue_outbox(
    db: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int | str,
    payload: dict[str, Any] | None = None,
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload_json=payload or {},
        max_attempts=get_settings().outbox_max_attempts,
    )
    db.add(event)
    return event


def enqueue_job(
    db: Session,
    job_type: str,
    payload: dict[str, Any] | None = None,
) -> BackgroundJob:
    job = BackgroundJob(
        job_type=job_type,
        payload_json=payload or {},
        max_attempts=get_settings().outbox_max_attempts,
    )
    db.add(job)
    return job


def mark_retryable(item: OutboxEvent | BackgroundJob, error: str) -> None:
    item.attempts += 1
    item.last_error = error[:1000]
    if item.attempts >= item.max_attempts:
        item.status = WorkStatus.dead_letter
        return
    item.status = WorkStatus.failed
    delay_seconds = min(300, 2 ** max(item.attempts, 1))
    if isinstance(item, BackgroundJob):
        item.next_run_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
    else:
        item.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
