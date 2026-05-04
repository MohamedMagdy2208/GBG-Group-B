from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rbac import require_admin, require_roles
from app.api.utils import invalidate_operational_caches, run_matching_for_lost_report
from app.models import (
    AuditSeverity,
    BackgroundJob,
    ChatMessage,
    ChatSession,
    ClaimVerification,
    FoundItem,
    FoundItemStatus,
    LostReport,
    LostReportStatus,
    Notification,
    OutboxEvent,
    User,
    UserRole,
    WorkStatus,
)
from app.schemas import BackgroundJobRead, DataRetentionRunResponse, DeepHealthResponse, OutboxEventRead, UserRead
from app.services.audit_service import log_audit_event
from app.services.azure_openai_service import azure_openai_service
from app.services.azure_search_service import azure_search_service
from app.services.cache_service import cache_service


router = APIRouter(prefix="/admin", tags=["admin operations"])
health_router = APIRouter(tags=["health"])


@router.get("/jobs", response_model=list[BackgroundJobRead])
def list_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.security)),
) -> list[BackgroundJob]:
    query = db.query(BackgroundJob)
    if status_filter:
        query = query.filter(BackgroundJob.status == status_filter)
    return query.order_by(BackgroundJob.created_at.desc()).limit(200).all()


@router.post("/jobs/{job_id}/retry", response_model=BackgroundJobRead)
def retry_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BackgroundJob:
    job = db.get(BackgroundJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job.status = WorkStatus.pending
    job.next_run_at = None
    job.last_error = None
    log_audit_event(db, action="admin.job_retry", entity_type="background_job", entity_id=job.id, actor=current_user, request=request)
    db.commit()
    db.refresh(job)
    return job


@router.get("/outbox", response_model=list[OutboxEventRead])
def list_outbox(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.security)),
) -> list[OutboxEvent]:
    query = db.query(OutboxEvent)
    if status_filter:
        query = query.filter(OutboxEvent.status == status_filter)
    return query.order_by(OutboxEvent.created_at.desc()).limit(200).all()


@router.post("/search/recreate-index")
async def recreate_search_index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.security)),
) -> dict[str, Any]:
    await azure_search_service.recreate_index()
    log_audit_event(
        db,
        action="admin.search_index_recreated",
        entity_type="search_index",
        actor=current_user,
        severity=AuditSeverity.warning,
        request=request,
    )
    db.commit()
    await invalidate_operational_caches()
    return {"status": "ok", "index": get_settings().azure_search_index_name}


@router.post("/search/reindex-lost-reports")
async def reindex_lost_reports(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.security)),
) -> dict[str, Any]:
    result = await _reindex_lost_reports(db)
    log_audit_event(
        db,
        action="admin.lost_reports_reindexed",
        entity_type="search_index",
        actor=current_user,
        metadata=result,
        request=request,
    )
    db.commit()
    await invalidate_operational_caches()
    return result


@router.post("/search/reindex-found-items")
async def reindex_found_items(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.security)),
) -> dict[str, Any]:
    result = await _reindex_found_items(db)
    log_audit_event(
        db,
        action="admin.found_items_reindexed",
        entity_type="search_index",
        actor=current_user,
        metadata=result,
        request=request,
    )
    db.commit()
    await invalidate_operational_caches()
    return result


@router.post("/search/reindex-all")
async def reindex_all_search_documents(
    request: Request,
    recreate_index: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.security)),
) -> dict[str, Any]:
    if recreate_index:
        await azure_search_service.recreate_index()
    lost = await _reindex_lost_reports(db)
    found = await _reindex_found_items(db)
    result = {
        "status": "ok" if not lost["failed"] and not found["failed"] else "partial",
        "recreated_index": recreate_index,
        "lost_reports": lost,
        "found_items": found,
    }
    log_audit_event(
        db,
        action="admin.search_reindex_all",
        entity_type="search_index",
        actor=current_user,
        severity=AuditSeverity.warning if recreate_index else AuditSeverity.info,
        metadata=result,
        request=request,
    )
    db.commit()
    await invalidate_operational_caches()
    return result


@router.post("/matching/rerun-all")
async def rerun_matching(
    request: Request,
    limit: int | None = Query(default=None, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.security)),
) -> dict[str, Any]:
    query = (
        db.query(LostReport)
        .filter(LostReport.status.notin_([LostReportStatus.resolved, LostReportStatus.rejected]))
        .order_by(LostReport.created_at.desc())
    )
    if limit:
        query = query.limit(limit)
    reports = query.all()
    created_or_updated = 0
    failed: list[dict[str, Any]] = []
    for report in reports:
        try:
            created_or_updated += len(await run_matching_for_lost_report(db, report))
        except Exception as exc:
            failed.append({"lost_report_id": report.id, "error": str(exc)})
    result = {
        "status": "ok" if not failed else "partial",
        "scanned_lost_reports": len(reports),
        "match_candidates_returned": created_or_updated,
        "failed": failed,
    }
    log_audit_event(
        db,
        action="admin.matching_rerun_all",
        entity_type="match_candidate",
        actor=current_user,
        severity=AuditSeverity.warning if failed else AuditSeverity.info,
        metadata=result,
        request=request,
    )
    db.commit()
    await invalidate_operational_caches()
    return result


@router.post("/data-retention/run", response_model=DataRetentionRunResponse)
def run_data_retention(
    request: Request,
    dry_run: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=get_settings().proof_document_retention_days)
    expired_chat_sessions = db.query(ChatSession).filter(ChatSession.created_at < cutoff).count()
    expired_chat_messages = (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.created_at < cutoff)
        .count()
    )
    affected = expired_chat_sessions + expired_chat_messages
    if not dry_run:
        # Conservative pilot behavior: only delete old unauthenticated chatbot transcripts.
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(db.query(ChatSession.id).filter(ChatSession.created_at < cutoff))).delete(synchronize_session=False)
        db.query(ChatSession).filter(ChatSession.created_at < cutoff).delete(synchronize_session=False)
    log_audit_event(
        db,
        action="admin.data_retention_run",
        entity_type="system",
        actor=current_user,
        severity=AuditSeverity.warning,
        metadata={"dry_run": dry_run, "affected_records": affected},
        request=request,
    )
    db.commit()
    return {
        "status": "ok",
        "dry_run": dry_run,
        "scanned_tables": ["chat_sessions", "chat_messages"],
        "affected_records": affected,
    }


@router.post("/users/{user_id}/disable", response_model=UserRead)
def disable_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot disable their own account")
    user.is_disabled = True
    log_audit_event(db, action="admin.user_disabled", entity_type="user", entity_id=user.id, actor=current_user, severity=AuditSeverity.warning, request=request)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}/data-export")
def export_user_data(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    lost_report_ids = [row[0] for row in db.query(LostReport.id).filter(LostReport.passenger_id == user_id).all()]
    notification_ids = [row[0] for row in db.query(Notification.id).filter(Notification.user_id == user_id).all()]
    chat_session_ids = [row[0] for row in db.query(ChatSession.id).filter(ChatSession.passenger_id == user_id).all()]
    claim_ids = [row[0] for row in db.query(ClaimVerification.id).filter(ClaimVerification.passenger_id == user_id).all()]
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone, "role": user.role.value, "is_disabled": user.is_disabled},
        "lost_report_ids": lost_report_ids,
        "notification_ids": notification_ids,
        "chat_session_ids": chat_session_ids,
        "claim_verification_ids": claim_ids,
    }


@router.post("/users/{user_id}/privacy-delete")
def privacy_delete_user(
    user_id: int,
    request: Request,
    dry_run: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role != UserRole.passenger:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only passenger accounts can use privacy delete")
    reports = db.query(LostReport).filter(LostReport.passenger_id == user_id).all()
    affected = {"user": 1, "lost_reports": len(reports)}
    if not dry_run:
        user.name = f"Deleted Passenger {user.id}"
        user.email = f"deleted-{user.id}@privacy.local"
        user.phone = None
        user.is_disabled = True
        for report in reports:
            report.contact_email = None
            report.contact_phone = None
        log_audit_event(
            db,
            action="admin.user_privacy_delete",
            entity_type="user",
            entity_id=user.id,
            actor=current_user,
            severity=AuditSeverity.critical,
            metadata={"affected": affected},
            request=request,
        )
        db.commit()
    return {"status": "ok", "dry_run": dry_run, "affected": affected}


@router.get("/system/providers")
def system_providers(_: User = Depends(require_roles(UserRole.admin, UserRole.security))) -> dict[str, Any]:
    return _provider_status()


def _provider_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "environment": settings.environment,
        "use_azure_services": settings.use_azure_services,
        "cache_backend": settings.cache_backend,
        "voice_provider": settings.voice_provider,
        "graph_rag_provider": settings.graph_rag_provider,
        "azure": {
            "openai_configured": bool(settings.azure_openai_endpoint and settings.azure_openai_chat_deployment),
            "openai_routes": azure_openai_service.route_deployments(),
            "search_configured": bool(settings.azure_search_endpoint and settings.azure_search_key),
            "blob_configured": bool(settings.azure_storage_connection_string or settings.azure_storage_account_name),
            "vision_configured": bool(settings.azure_ai_vision_endpoint and settings.azure_ai_vision_key),
            "communication_configured": bool(settings.azure_communication_connection_string),
            "application_insights_configured": bool(settings.applicationinsights_connection_string),
        },
    }


async def _reindex_lost_reports(db: Session) -> dict[str, Any]:
    reports = db.query(LostReport).order_by(LostReport.id).all()
    indexed = 0
    failed: list[dict[str, Any]] = []
    for report in reports:
        try:
            report.search_document_id = await azure_search_service.index_lost_report(report)
            db.add(report)
            indexed += 1
        except Exception as exc:
            failed.append({"lost_report_id": report.id, "error": str(exc)})
    return {"status": "ok" if not failed else "partial", "scanned": len(reports), "indexed": indexed, "failed": failed}


async def _reindex_found_items(db: Session) -> dict[str, Any]:
    items = (
        db.query(FoundItem)
        .filter(FoundItem.status.notin_([FoundItemStatus.disposed]))
        .order_by(FoundItem.id)
        .all()
    )
    indexed = 0
    failed: list[dict[str, Any]] = []
    for item in items:
        try:
            item.search_document_id = await azure_search_service.index_found_item(item)
            db.add(item)
            indexed += 1
        except Exception as exc:
            failed.append({"found_item_id": item.id, "error": str(exc)})
    return {"status": "ok" if not failed else "partial", "scanned": len(items), "indexed": indexed, "failed": failed}


@health_router.get("/health/ready/deep", response_model=DeepHealthResponse)
async def deep_ready(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    checks: dict[str, dict[str, Any]] = {}
    checks["postgres"] = _check_postgres(db)
    checks["redis"] = await _check_redis()
    checks["blob"] = _check_blob()
    checks["search"] = _check_search()
    checks["outbox"] = _check_outbox(db)
    checks["worker_queue"] = _check_worker_queue(db)
    if _is_authenticated_admin(request, db):
        checks["providers"] = {"status": "ok", "details": _provider_status()}
    overall = "ready" if all(check["status"] == "ok" for check in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


def _is_authenticated_admin(request: Request, db: Session) -> bool:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return False
    from app.core.security import decode_access_token

    token = auth.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except Exception:
        return False
    user = db.get(User, user_id)
    return bool(user and user.role.value in {"admin", "security"})


def _check_postgres(db: Session) -> dict[str, Any]:
    try:
        db.execute(text("select 1")).scalar_one()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


async def _check_redis() -> dict[str, Any]:
    try:
        key = "health:redis"
        await cache_service.set_json(key, {"ok": True}, 15)
        value = await cache_service.get_json(key)
        return {"status": "ok" if value else "failed"}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _check_outbox(db: Session) -> dict[str, Any]:
    pending = db.query(OutboxEvent).filter(OutboxEvent.status.in_([WorkStatus.pending, WorkStatus.failed])).count()
    dead = db.query(OutboxEvent).filter(OutboxEvent.status == WorkStatus.dead_letter).count()
    return {"status": "ok" if dead == 0 else "failed", "pending": pending, "dead_letter": dead}


def _check_worker_queue(db: Session) -> dict[str, Any]:
    pending = db.query(BackgroundJob).filter(BackgroundJob.status.in_([WorkStatus.pending, WorkStatus.failed])).count()
    dead = db.query(BackgroundJob).filter(BackgroundJob.status == WorkStatus.dead_letter).count()
    return {"status": "ok" if dead == 0 else "failed", "pending": pending, "dead_letter": dead}


def _check_blob() -> dict[str, Any]:
    settings = get_settings()
    if not settings.use_azure_services:
        settings.local_upload_dir.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "mode": "local", "path": str(settings.local_upload_dir)}
    configured = bool(settings.azure_storage_connection_string or settings.azure_storage_account_name)
    return {"status": "ok" if configured else "failed", "mode": "azure", "configured": configured}


def _check_search() -> dict[str, Any]:
    settings = get_settings()
    if not settings.use_azure_services:
        return {"status": "ok", "mode": "local"}
    configured = bool(settings.azure_search_endpoint and settings.azure_search_key and settings.azure_search_index_name)
    return {"status": "ok" if configured else "failed", "mode": "azure", "configured": configured}
