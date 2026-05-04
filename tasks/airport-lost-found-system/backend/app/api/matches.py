from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.utils import add_custody_event, invalidate_operational_caches, run_matching_for_found_item, run_matching_for_lost_report
from app.core.database import get_db
from app.core.idempotency import find_idempotent_response, get_idempotency_key, request_hash, store_idempotent_response
from app.core.rbac import require_staff
from app.models import AuditSeverity, CustodyAction, FoundItem, FoundItemStatus, LostReport, LostReportStatus, MatchCandidate, MatchStatus, User
from app.schemas import MatchActionRequest, MatchCandidateRead
from app.services.audit_service import log_audit_event
from app.services.azure_search_service import azure_search_service
from app.services.outbox_service import enqueue_outbox


router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchCandidateRead])
def list_matches(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[MatchCandidate]:
    query = db.query(MatchCandidate).options(joinedload(MatchCandidate.lost_report), joinedload(MatchCandidate.found_item))
    if status_filter:
        query = query.filter(MatchCandidate.status == status_filter)
    return query.order_by(MatchCandidate.match_score.desc(), MatchCandidate.created_at.desc()).all()


@router.get("/{match_id}", response_model=MatchCandidateRead)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> MatchCandidate:
    candidate = (
        db.query(MatchCandidate)
        .options(joinedload(MatchCandidate.lost_report), joinedload(MatchCandidate.found_item))
        .filter(MatchCandidate.id == match_id)
        .one_or_none()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return candidate


@router.post("/bulk/approve")
async def bulk_approve(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    ids = [int(item) for item in payload.get("ids", []) if item is not None]
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids is required")
    approved: list[int] = []
    skipped: list[dict] = []
    for match_id in ids:
        candidate = (
            db.query(MatchCandidate)
            .filter(MatchCandidate.id == match_id)
            .with_for_update()
            .one_or_none()
        )
        if not candidate:
            skipped.append({"id": match_id, "reason": "not_found"})
            continue
        if candidate.status == MatchStatus.approved:
            approved.append(candidate.id)
            continue
        if candidate.found_item.risk_level.value != "normal":
            skipped.append({"id": match_id, "reason": f"risk_{candidate.found_item.risk_level.value}"})
            continue
        candidate.status = MatchStatus.approved
        candidate.review_notes = "Bulk approve"
        candidate.reviewed_by_staff_id = current_user.id
        candidate.lost_report.status = LostReportStatus.matched
        candidate.found_item.status = FoundItemStatus.claimed
        add_custody_event(db, candidate.found_item, CustodyAction.claimed, current_user.id, candidate.found_item.storage_location, "Bulk approve")
        log_audit_event(
            db,
            action="match.bulk_approved",
            entity_type="match_candidate",
            entity_id=candidate.id,
            actor=current_user,
            severity=AuditSeverity.info,
            metadata={"bulk_count": len(ids)},
            request=request,
        )
        approved.append(candidate.id)
    db.commit()
    await invalidate_operational_caches()
    return {"approved": approved, "skipped": skipped}


@router.post("/bulk/reject")
async def bulk_reject(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    ids = [int(item) for item in payload.get("ids", []) if item is not None]
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids is required")
    rejected: list[int] = []
    for match_id in ids:
        candidate = db.get(MatchCandidate, match_id)
        if not candidate or candidate.status == MatchStatus.rejected:
            continue
        candidate.status = MatchStatus.rejected
        candidate.review_notes = "Bulk reject"
        candidate.reviewed_by_staff_id = current_user.id
        log_audit_event(
            db,
            action="match.bulk_rejected",
            entity_type="match_candidate",
            entity_id=candidate.id,
            actor=current_user,
            severity=AuditSeverity.info,
            metadata={"bulk_count": len(ids)},
            request=request,
        )
        rejected.append(candidate.id)
    db.commit()
    await invalidate_operational_caches()
    return {"rejected": rejected}


@router.post("/run", response_model=list[MatchCandidateRead])
async def run_all_matches(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[MatchCandidate]:
    candidates: list[MatchCandidate] = []
    for report in db.query(LostReport).all():
        candidates.extend(await run_matching_for_lost_report(db, report))
    return candidates


@router.post("/{match_id}/approve", response_model=MatchCandidateRead)
async def approve_match(
    match_id: int,
    payload: MatchActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> MatchCandidate:
    idempotency_key = get_idempotency_key(request)
    hash_value = request_hash({"match_id": match_id, "payload": payload.model_dump(mode="json"), "staff_id": current_user.id})
    cached = find_idempotent_response(db, "match.approve", idempotency_key, hash_value)
    if cached and cached.get("match_candidate_id"):
        candidate = db.get(MatchCandidate, cached["match_candidate_id"])
        if candidate:
            return candidate

    candidate = (
        db.query(MatchCandidate)
        .filter(MatchCandidate.id == match_id)
        .with_for_update()
        .one_or_none()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if candidate.status == MatchStatus.approved:
        # Another concurrent staff click already approved; return current state.
        return candidate
    candidate.status = MatchStatus.approved
    candidate.review_notes = payload.review_notes
    candidate.reviewed_by_staff_id = current_user.id
    candidate.lost_report.status = LostReportStatus.matched
    candidate.found_item.status = FoundItemStatus.claimed
    add_custody_event(db, candidate.found_item, CustodyAction.claimed, current_user.id, candidate.found_item.storage_location, "Match approved")
    log_audit_event(
        db,
        action="match.approved",
        entity_type="match_candidate",
        entity_id=candidate.id,
        actor=current_user,
        severity=AuditSeverity.warning if candidate.found_item.risk_level.value != "normal" else AuditSeverity.info,
        metadata={"match_score": candidate.match_score, "risk_level": candidate.found_item.risk_level.value},
        request=request,
    )
    enqueue_outbox(
        db,
        "match.approved",
        "match_candidate",
        candidate.id,
        {"match_score": candidate.match_score, "risk_level": candidate.found_item.risk_level.value},
    )
    store_idempotent_response(db, "match.approve", idempotency_key, hash_value, {"match_candidate_id": candidate.id})
    await azure_search_service.index_found_item(candidate.found_item)
    await azure_search_service.index_lost_report(candidate.lost_report)
    db.commit()
    db.refresh(candidate)
    await invalidate_operational_caches()
    return candidate


@router.post("/{match_id}/reject", response_model=MatchCandidateRead)
async def reject_match(
    match_id: int,
    payload: MatchActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> MatchCandidate:
    candidate = db.get(MatchCandidate, match_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    candidate.status = MatchStatus.rejected
    candidate.review_notes = payload.review_notes
    candidate.reviewed_by_staff_id = current_user.id
    log_audit_event(
        db,
        action="match.rejected",
        entity_type="match_candidate",
        entity_id=candidate.id,
        actor=current_user,
        severity=AuditSeverity.info,
        metadata={"match_score": candidate.match_score},
        request=request,
    )
    db.commit()
    db.refresh(candidate)
    await invalidate_operational_caches()
    return candidate


@router.post("/{match_id}/needs-more-info", response_model=MatchCandidateRead)
async def needs_more_info(
    match_id: int,
    payload: MatchActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> MatchCandidate:
    candidate = db.get(MatchCandidate, match_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    candidate.status = MatchStatus.needs_more_info
    candidate.review_notes = payload.review_notes
    candidate.reviewed_by_staff_id = current_user.id
    log_audit_event(
        db,
        action="match.needs_more_info",
        entity_type="match_candidate",
        entity_id=candidate.id,
        actor=current_user,
        severity=AuditSeverity.info,
        metadata={"match_score": candidate.match_score},
        request=request,
    )
    db.commit()
    db.refresh(candidate)
    await invalidate_operational_caches()
    return candidate
