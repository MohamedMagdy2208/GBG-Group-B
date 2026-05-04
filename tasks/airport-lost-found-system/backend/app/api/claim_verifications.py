from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.chat import contact_matches_report
from app.api.utils import add_custody_event, invalidate_operational_caches
from app.core.config import get_settings
from app.core.database import get_db
from app.core.idempotency import find_idempotent_response, get_idempotency_key, request_hash, store_idempotent_response
from app.core.rbac import require_staff
from app.core.security import mask_phone
from app.models import (
    AuditSeverity,
    ClaimVerification,
    ClaimVerificationStatus,
    CustodyAction,
    FoundItemStatus,
    LostReportStatus,
    MatchCandidate,
    MatchStatus,
    User,
)
from app.schemas import (
    ClaimEvidenceSubmit,
    ClaimReleaseRequest,
    ClaimReviewRequest,
    ClaimVerificationCreate,
    ClaimVerificationRead,
    FraudScoreResponse,
)
from app.services.audit_service import log_audit_event
from app.services.azure_openai_service import azure_openai_service
from app.services.azure_search_service import azure_search_service
from app.services.cache_service import cache_service
from app.services.fraud_risk_service import fraud_risk_service
from app.services.outbox_service import enqueue_outbox


router = APIRouter(tags=["claim verification"])


@router.post("/matches/{match_id}/claim-verification", response_model=ClaimVerificationRead)
async def create_claim_verification(
    match_id: int,
    request: Request,
    payload: ClaimVerificationCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> ClaimVerification:
    idempotency_key = get_idempotency_key(request)
    payload_data = payload.model_dump(mode="json") if payload else {}
    hash_value = request_hash({"match_id": match_id, "payload": payload_data, "staff_id": current_user.id})
    cached = find_idempotent_response(db, "claim_verification.create", idempotency_key, hash_value)
    if cached and cached.get("claim_verification_id"):
        claim = db.get(ClaimVerification, cached["claim_verification_id"])
        if claim:
            return claim

    candidate = _get_candidate(db, match_id)
    existing = (
        db.query(ClaimVerification)
        .options(joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.lost_report), joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.found_item))
        .filter(ClaimVerification.match_candidate_id == match_id)
        .one_or_none()
    )
    if existing:
        return existing

    questions = (payload.verification_questions_json if payload else None)
    if not questions:
        try:
            generated = await azure_openai_service.generate_verification_questions(
                candidate.found_item.ai_extracted_attributes_json or {},
                candidate.found_item.vision_tags_json or [],
                candidate.found_item.vision_ocr_text,
                category=candidate.found_item.category,
            )
            questions = [entry["question"] for entry in generated]
            # Stash expected answers privately for staff (NEVER returned to passenger).
            candidate.found_item.ai_extracted_attributes_json = {
                **(candidate.found_item.ai_extracted_attributes_json or {}),
                "_verification_keys": [entry.get("expected_keywords", []) for entry in generated],
            }
            db.add(candidate.found_item)
        except Exception:
            questions = _default_questions(candidate)
    if not questions:
        questions = _default_questions(candidate)
    risk = fraud_risk_service.score_match(db, candidate)
    claim = ClaimVerification(
        match_candidate_id=candidate.id,
        lost_report_id=candidate.lost_report_id,
        found_item_id=candidate.found_item_id,
        passenger_id=candidate.lost_report.passenger_id,
        verification_questions_json=questions,
        fraud_score=risk["fraud_score"],
        fraud_flags_json=risk["fraud_flags"],
        status=ClaimVerificationStatus.blocked if risk["release_blocked"] else ClaimVerificationStatus.pending,
    )
    db.add(claim)
    log_audit_event(
        db,
        action="claim_verification.created",
        entity_type="claim_verification",
        entity_id=None,
        actor=current_user,
        severity=AuditSeverity.warning if risk["release_blocked"] else AuditSeverity.info,
        metadata={"match_candidate_id": match_id, "fraud_score": risk["fraud_score"]},
        request=request,
    )
    db.commit()
    db.refresh(claim)
    await invalidate_operational_caches()
    return claim


@router.get("/claim-verifications", response_model=list[ClaimVerificationRead])
async def list_claim_verifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[ClaimVerification]:
    claims = (
        db.query(ClaimVerification)
        .options(joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.lost_report), joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.found_item))
        .order_by(ClaimVerification.updated_at.desc())
        .all()
    )
    return claims


@router.get("/claim-verifications/{claim_id}", response_model=ClaimVerificationRead)
def get_claim_verification(
    claim_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> ClaimVerification:
    claim = (
        db.query(ClaimVerification)
        .options(joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.lost_report), joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.found_item))
        .filter(ClaimVerification.id == claim_id)
        .one_or_none()
    )
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim verification not found")
    return claim


@router.post("/claim-verifications/{claim_id}/submit-evidence", response_model=ClaimVerificationRead)
async def submit_claim_evidence(
    claim_id: int,
    payload: ClaimEvidenceSubmit,
    request: Request,
    db: Session = Depends(get_db),
) -> ClaimVerification:
    claim = _get_claim(db, claim_id)
    if not contact_matches_report(claim.lost_report, payload.contact):
        risk = fraud_risk_service.score_match(db, claim.match_candidate, payload.contact, payload.passenger_answers_json)
        claim.fraud_score = risk["fraud_score"]
        claim.fraud_flags_json = risk["fraud_flags"]
        claim.status = ClaimVerificationStatus.blocked
        log_audit_event(
            db,
            action="claim_verification.contact_failed",
            entity_type="claim_verification",
            entity_id=claim.id,
            severity=AuditSeverity.warning,
            metadata={"fraud_score": risk["fraud_score"]},
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim contact verification failed")

    risk = fraud_risk_service.score_match(db, claim.match_candidate, payload.contact, payload.passenger_answers_json)
    claim.passenger_answers_json = payload.passenger_answers_json
    claim.proof_blob_urls_json = payload.proof_blob_urls_json
    claim.submitted_at = datetime.now(UTC)
    claim.fraud_score = risk["fraud_score"]
    claim.fraud_flags_json = risk["fraud_flags"]
    claim.status = ClaimVerificationStatus.blocked if risk["release_blocked"] else ClaimVerificationStatus.submitted
    log_audit_event(
        db,
        action="claim_verification.evidence_submitted",
        entity_type="claim_verification",
        entity_id=claim.id,
        severity=AuditSeverity.warning if risk["release_blocked"] else AuditSeverity.info,
        metadata={"fraud_score": risk["fraud_score"], "proof_count": len(payload.proof_blob_urls_json)},
        request=request,
    )
    db.commit()
    db.refresh(claim)
    await invalidate_operational_caches()
    return claim


@router.post("/claim-verifications/{claim_id}/approve", response_model=ClaimVerificationRead)
async def approve_claim_verification(
    claim_id: int,
    payload: ClaimReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> ClaimVerification:
    claim = _get_claim(db, claim_id)
    claim.status = ClaimVerificationStatus.approved
    claim.staff_review_notes = payload.review_notes
    claim.release_checklist_json = payload.release_checklist_json
    claim.approved_by_staff_id = current_user.id
    claim.reviewed_at = datetime.now(UTC)
    log_audit_event(
        db,
        action="claim_verification.approved",
        entity_type="claim_verification",
        entity_id=claim.id,
        actor=current_user,
        severity=AuditSeverity.warning if claim.fraud_score >= get_settings().fraud_high_risk_threshold else AuditSeverity.info,
        metadata={"fraud_score": claim.fraud_score},
        request=request,
    )
    db.commit()
    db.refresh(claim)
    await invalidate_operational_caches()
    return claim


@router.post("/claim-verifications/{claim_id}/reject", response_model=ClaimVerificationRead)
async def reject_claim_verification(
    claim_id: int,
    payload: ClaimReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> ClaimVerification:
    claim = _get_claim(db, claim_id)
    claim.status = ClaimVerificationStatus.rejected
    claim.staff_review_notes = payload.review_notes
    claim.reviewed_at = datetime.now(UTC)
    log_audit_event(
        db,
        action="claim_verification.rejected",
        entity_type="claim_verification",
        entity_id=claim.id,
        actor=current_user,
        severity=AuditSeverity.warning,
        metadata={"fraud_score": claim.fraud_score},
        request=request,
    )
    db.commit()
    db.refresh(claim)
    await invalidate_operational_caches()
    return claim


@router.post("/matches/{match_id}/release", response_model=ClaimVerificationRead)
async def release_match(
    match_id: int,
    payload: ClaimReleaseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> ClaimVerification:
    idempotency_key = get_idempotency_key(request)
    hash_value = request_hash({"match_id": match_id, "payload": payload.model_dump(mode="json"), "staff_id": current_user.id})
    cached = find_idempotent_response(db, "match.release", idempotency_key, hash_value)
    if cached and cached.get("claim_verification_id"):
        claim = db.get(ClaimVerification, cached["claim_verification_id"])
        if claim:
            return claim

    candidate = _get_candidate(db, match_id)
    claim = (
        db.query(ClaimVerification)
        .filter(ClaimVerification.match_candidate_id == candidate.id)
        .one_or_none()
    )
    if not claim:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Create and approve claim verification before release")
    if claim.status != ClaimVerificationStatus.approved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Claim verification must be approved before release")
    if not _release_checklist_complete(payload.release_checklist_json):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Release checklist is incomplete")

    claim.status = ClaimVerificationStatus.released
    claim.release_checklist_json = payload.release_checklist_json
    claim.staff_review_notes = payload.review_notes or claim.staff_review_notes
    claim.released_to_name = payload.released_to_name
    claim.released_to_contact_masked = mask_phone(payload.released_to_contact)
    claim.released_by_staff_id = current_user.id
    claim.released_at = datetime.now(UTC)
    candidate.status = MatchStatus.approved
    candidate.found_item.status = FoundItemStatus.released
    candidate.lost_report.status = LostReportStatus.resolved
    add_custody_event(
        db,
        candidate.found_item,
        CustodyAction.released,
        current_user.id,
        candidate.found_item.storage_location,
        f"Released after claim verification {claim.id}",
    )
    log_audit_event(
        db,
        action="item.released",
        entity_type="found_item",
        entity_id=candidate.found_item_id,
        actor=current_user,
        severity=AuditSeverity.critical if claim.fraud_score >= get_settings().fraud_high_risk_threshold else AuditSeverity.info,
        metadata={"claim_verification_id": claim.id, "match_candidate_id": match_id, "fraud_score": claim.fraud_score},
        request=request,
    )
    enqueue_outbox(
        db,
        "item.released",
        "found_item",
        candidate.found_item_id,
        {
            "claim_verification_id": claim.id,
            "match_candidate_id": match_id,
            "fraud_score": claim.fraud_score,
            "lost_report_id": candidate.lost_report_id,
            "report_code": candidate.lost_report.report_code if candidate.lost_report else None,
        },
    )
    store_idempotent_response(db, "match.release", idempotency_key, hash_value, {"claim_verification_id": claim.id})
    await azure_search_service.index_found_item(candidate.found_item)
    await azure_search_service.index_lost_report(candidate.lost_report)
    db.commit()
    db.refresh(claim)
    await invalidate_operational_caches()
    return claim


@router.get("/matches/{match_id}/fraud-score", response_model=FraudScoreResponse)
async def fraud_score_for_match(
    match_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    candidate = _get_candidate(db, match_id)
    cache_key = f"fraud:match:{match_id}"
    cached = await cache_service.get_json(cache_key)
    if cached:
        return cached
    risk = fraud_risk_service.score_match(db, candidate)
    data = {
        "match_candidate_id": candidate.id,
        "fraud_score": risk["fraud_score"],
        "fraud_flags": risk["fraud_flags"],
        "risk_level": risk["risk_level"],
        "release_blocked": risk["release_blocked"],
    }
    await cache_service.set_json(cache_key, data, 300)
    return data


def _get_candidate(db: Session, match_id: int) -> MatchCandidate:
    candidate = (
        db.query(MatchCandidate)
        .options(joinedload(MatchCandidate.lost_report), joinedload(MatchCandidate.found_item))
        .filter(MatchCandidate.id == match_id)
        .one_or_none()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return candidate


def _get_claim(db: Session, claim_id: int) -> ClaimVerification:
    claim = (
        db.query(ClaimVerification)
        .options(joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.lost_report), joinedload(ClaimVerification.match_candidate).joinedload(MatchCandidate.found_item))
        .filter(ClaimVerification.id == claim_id)
        .one_or_none()
    )
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim verification not found")
    return claim


def _default_questions(candidate: MatchCandidate) -> list[str]:
    title = candidate.lost_report.item_title or "the item"
    return [
        f"Describe a unique detail or mark on {title}.",
        "Where and when did you last remember having it?",
        "Can you provide proof such as a receipt, serial number, photo, or boarding pass?",
    ]


def _release_checklist_complete(checklist: dict) -> bool:
    required = ["identity_checked", "proof_checked", "passenger_signed", "custody_updated"]
    return all(bool(checklist.get(key)) for key in required)
