from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.utils import enrich_lost_report, invalidate_operational_caches, run_matching_for_lost_report
from app.core.config import get_settings
from app.core.database import get_db
from app.core.idempotency import find_idempotent_response, get_idempotency_key, request_hash, store_idempotent_response
from app.core.rate_limit import rate_limit
from app.core.rbac import get_current_user, get_optional_user
from app.models import LostReport, User, UserRole
from app.schemas import LostReportCreate, LostReportRead, LostReportUpdate, MatchCandidateRead
from app.services.azure_openai_service import azure_openai_service
from app.services.azure_search_service import azure_search_service
from app.services.azure_vision_service import azure_vision_service
from app.services.outbox_service import enqueue_job, enqueue_outbox


class PhotoOnlyLostReportRequest(BaseModel):
    image_url: str
    contact_email: str | None = None
    contact_phone: str | None = None
    lost_location: str | None = None


router = APIRouter(prefix="/lost-reports", tags=["lost reports"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return None


def _can_access_report(user: User, report: LostReport) -> bool:
    if user.role in {UserRole.staff, UserRole.admin, UserRole.security}:
        return True
    return report.passenger_id == user.id


@router.post("", response_model=LostReportRead, dependencies=[Depends(rate_limit("lost_report_create", get_settings().rate_limit_public_per_minute, 60))])
async def create_lost_report(
    payload: LostReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> LostReport:
    idempotency_key = get_idempotency_key(request)
    hash_value = request_hash({"payload": payload.model_dump(mode="json"), "passenger_id": current_user.id if current_user else None})
    cached = find_idempotent_response(db, "lost_report.create", idempotency_key, hash_value)
    if cached and cached.get("lost_report_id"):
        report = db.get(LostReport, cached["lost_report_id"])
        if report:
            return report

    report = LostReport(
        **payload.model_dump(),
        passenger_id=current_user.id if current_user else None,
        created_from_ip=_client_ip(request),
    )
    db.add(report)
    await enrich_lost_report(db, report)
    enqueue_outbox(db, "lost_report.created", "lost_report", report.id, {"report_code": report.report_code, "category": report.category})
    enqueue_job(db, "graph.summary.generate", {"entity_type": "lost_report", "entity_id": report.id})
    enqueue_job(db, "matching.lost_report", {"lost_report_id": report.id})
    store_idempotent_response(db, "lost_report.create", idempotency_key, hash_value, {"lost_report_id": report.id}, status.HTTP_201_CREATED)
    db.commit()
    db.refresh(report)
    await invalidate_operational_caches()
    return report


@router.get("", response_model=list[LostReportRead])
def list_lost_reports(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LostReport]:
    query = db.query(LostReport)
    if current_user.role == UserRole.passenger:
        query = query.filter(LostReport.passenger_id == current_user.id)
    if status_filter:
        query = query.filter(LostReport.status == status_filter)
    if category:
        query = query.filter(LostReport.category == category)
    return query.order_by(LostReport.created_at.desc()).all()


@router.get("/{report_id}", response_model=LostReportRead)
def get_lost_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LostReport:
    report = db.get(LostReport, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lost report not found")
    if not _can_access_report(current_user, report):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return report


@router.put("/{report_id}", response_model=LostReportRead)
async def update_lost_report(
    report_id: int,
    payload: LostReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LostReport:
    report = db.get(LostReport, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lost report not found")
    if not _can_access_report(current_user, report):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, key, value)
    await enrich_lost_report(db, report)
    db.commit()
    db.refresh(report)
    await invalidate_operational_caches()
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lost_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    report = db.get(LostReport, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lost report not found")
    if not _can_access_report(current_user, report):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if report.search_document_id:
        await azure_search_service.delete_document(report.search_document_id)
    db.delete(report)
    db.commit()
    await invalidate_operational_caches()


@router.post(
    "/photo-only",
    response_model=LostReportRead,
    dependencies=[Depends(rate_limit("lost_report_photo", get_settings().rate_limit_public_per_minute, 60))],
)
async def create_lost_report_from_photo(
    payload: PhotoOnlyLostReportRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> LostReport:
    if not payload.contact_email and not payload.contact_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contact_email or contact_phone is required")
    vision = await azure_vision_service.analyze_uploaded_item_image(payload.image_url)
    description = await azure_openai_service.describe_item_from_vision(vision)
    report = LostReport(
        item_title=description["item_title"],
        category=description.get("category"),
        raw_description=description.get("raw_description") or "Photo-only report — staff to review image.",
        color=description.get("color"),
        brand=description.get("brand"),
        lost_location=payload.lost_location,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        proof_blob_url=payload.image_url,
        passenger_id=current_user.id if current_user else None,
        created_from_ip=_client_ip(request),
    )
    db.add(report)
    await enrich_lost_report(db, report)
    enqueue_outbox(db, "lost_report.created", "lost_report", report.id, {"report_code": report.report_code, "category": report.category, "source": "photo_only"})
    enqueue_job(db, "matching.lost_report", {"lost_report_id": report.id})
    db.commit()
    db.refresh(report)
    await invalidate_operational_caches()
    return report


@router.post("/{report_id}/run-matching", response_model=list[MatchCandidateRead])
async def run_matching(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    report = db.get(LostReport, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lost report not found")
    if not _can_access_report(current_user, report):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return await run_matching_for_lost_report(db, report)
