from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rbac import require_staff
from app.models import AirportLocation, ClaimVerification, FoundItem, FoundItemStatus, LostReport, LostReportStatus, MatchCandidate, User
from app.schemas import AnalyticsSummary
from app.services.ai_usage_service import ai_usage_service
from app.services.cache_service import cache_service


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    settings = get_settings()
    cached = await cache_service.get_json("analytics:summary")
    if cached:
        return cached
    avg_score = db.query(func.avg(MatchCandidate.match_score)).scalar() or 0
    data = {
        "open_lost_reports": db.query(LostReport).filter(LostReport.status == LostReportStatus.open).count(),
        "registered_found_items": db.query(FoundItem).filter(FoundItem.status == FoundItemStatus.registered).count(),
        "pending_matches": db.query(MatchCandidate).filter(MatchCandidate.status == "pending").count(),
        "high_confidence_matches": db.query(MatchCandidate).filter(MatchCandidate.confidence_level == "high").count(),
        "released_items": db.query(FoundItem).filter(FoundItem.status == FoundItemStatus.released).count(),
        "average_match_score": round(float(avg_score), 2),
    }
    await cache_service.set_json("analytics:summary", data, settings.cache_analytics_ttl_seconds)
    return data


@router.get("/items-by-category")
async def items_by_category(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> list[dict]:
    counts = Counter()
    for value, count in db.query(LostReport.category, func.count(LostReport.id)).group_by(LostReport.category).all():
        counts[value or "Unknown"] += count
    for value, count in db.query(FoundItem.category, func.count(FoundItem.id)).group_by(FoundItem.category).all():
        counts[value or "Unknown"] += count
    return [{"category": category, "count": count} for category, count in counts.most_common()]


@router.get("/items-by-location")
async def items_by_location(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> list[dict]:
    counts = Counter()
    for value, count in db.query(LostReport.lost_location, func.count(LostReport.id)).group_by(LostReport.lost_location).all():
        counts[value or "Unknown"] += count
    for value, count in db.query(FoundItem.found_location, func.count(FoundItem.id)).group_by(FoundItem.found_location).all():
        counts[value or "Unknown"] += count
    return [{"location": location, "count": count} for location, count in counts.most_common()]


@router.get("/match-performance")
async def match_performance(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> dict:
    total = db.query(MatchCandidate).count()
    approved = db.query(MatchCandidate).filter(MatchCandidate.status == "approved").count()
    rejected = db.query(MatchCandidate).filter(MatchCandidate.status == "rejected").count()
    pending = db.query(MatchCandidate).filter(MatchCandidate.status == "pending").count()
    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "approval_rate": round((approved / total) * 100, 2) if total else 0,
    }


@router.get("/high-loss-areas")
async def high_loss_areas(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> list[dict]:
    rows = (
        db.query(LostReport.lost_location, func.count(LostReport.id).label("count"))
        .group_by(LostReport.lost_location)
        .order_by(func.count(LostReport.id).desc())
        .limit(10)
        .all()
    )
    known = {location.name: location.type.value for location in db.query(AirportLocation).all()}
    return [{"location": location or "Unknown", "type": known.get(location or "", "other"), "count": count} for location, count in rows]


@router.get("/ai-usage")
async def ai_usage(_: User = Depends(require_staff)) -> dict:
    return await ai_usage_service.summary()


@router.get("/fraud-risk")
async def fraud_risk(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> dict:
    settings = get_settings()
    cached = await cache_service.get_json("analytics:fraud-risk")
    if cached:
        return cached
    total_claims = db.query(ClaimVerification).count()
    high_risk = db.query(ClaimVerification).filter(ClaimVerification.fraud_score >= settings.fraud_high_risk_threshold).count()
    blocked = db.query(ClaimVerification).filter(ClaimVerification.status == "blocked").count()
    avg_score = db.query(func.avg(ClaimVerification.fraud_score)).scalar() or 0
    recent = (
        db.query(ClaimVerification)
        .order_by(ClaimVerification.updated_at.desc())
        .limit(5)
        .all()
    )
    data = {
        "total_claims": total_claims,
        "high_risk_claims": high_risk,
        "blocked_claims": blocked,
        "average_fraud_score": round(float(avg_score), 2),
        "recent": [
            {
                "id": claim.id,
                "match_candidate_id": claim.match_candidate_id,
                "status": claim.status.value,
                "fraud_score": claim.fraud_score,
                "fraud_flags": claim.fraud_flags_json,
            }
            for claim in recent
        ],
    }
    await cache_service.set_json("analytics:fraud-risk", data, settings.cache_analytics_ttl_seconds)
    return data
