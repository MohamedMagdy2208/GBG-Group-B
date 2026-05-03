import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ConfidenceLevel,
    CustodyAction,
    CustodyEvent,
    FoundItem,
    FoundItemStatus,
    LostReport,
    LostReportStatus,
    MatchCandidate,
)
from app.services.azure_openai_service import azure_openai_service
from app.services.azure_search_service import azure_search_service
from app.services.azure_vision_service import azure_vision_service
from app.services.cache_service import cache_service
from app.services.matching_engine import matching_engine
from app.services.outbox_service import enqueue_outbox


logger = logging.getLogger(__name__)


async def invalidate_operational_caches() -> None:
    await cache_service.delete_pattern("analytics:*")
    await cache_service.delete_pattern("status:*")
    await cache_service.delete_pattern("match-preview:*")
    await cache_service.delete_pattern("fraud:*")
    await cache_service.delete_pattern("claims:*")
    await cache_service.delete_pattern("graph-context:*")


async def enrich_lost_report(db: Session, report: LostReport) -> LostReport:
    text = " ".join(filter(None, [report.item_title, report.category, report.raw_description, report.lost_location, report.flight_number]))
    try:
        attrs = await azure_openai_service.extract_structured_attributes(text)
    except Exception:
        logger.exception("AI attribute extraction failed; using local fallback", extra={"event": "ai_extract_fallback"})
        attrs = azure_openai_service.fallback_extract_structured_attributes(text)
    try:
        report.ai_clean_description = await azure_openai_service.clean_item_description(report.raw_description)
    except Exception:
        logger.exception("AI description cleaning failed; using raw description", extra={"event": "ai_clean_fallback"})
        report.ai_clean_description = " ".join((report.raw_description or "").split())
    report.ai_extracted_attributes_json = attrs
    report.category = report.category or attrs.get("item_type")
    report.brand = report.brand or attrs.get("brand")
    report.model = report.model or attrs.get("model")
    report.color = report.color or attrs.get("color")
    report.flight_number = report.flight_number or attrs.get("flight_number")
    try:
        report.embedding_vector_id, _ = await azure_openai_service.generate_embedding(text)
    except Exception:
        logger.exception("AI embedding failed; using local fallback vector id", extra={"event": "ai_embedding_fallback"})
        report.embedding_vector_id, _ = azure_openai_service.fallback_embedding(text)
    db.flush()
    try:
        report.search_document_id = await azure_search_service.index_lost_report(report)
    except Exception:
        logger.exception("Azure Search indexing failed for lost report", extra={"event": "search_index_fallback"})
    db.add(report)
    return report


async def enrich_found_item(db: Session, item: FoundItem) -> FoundItem:
    item.vision_tags_json = item.vision_tags_json or []
    if item.image_blob_url:
        try:
            vision = await azure_vision_service.analyze_uploaded_item_image(item.image_blob_url)
            item.vision_tags_json = vision.get("tags", [])
            item.vision_ocr_text = vision.get("ocr_text")
        except Exception:
            logger.exception("Azure Vision analysis failed; continuing without image analysis", extra={"event": "vision_fallback"})
    tags = " ".join(tag.get("name", "") for tag in item.vision_tags_json if isinstance(tag, dict))
    text = " ".join(
        filter(None, [item.item_title, item.category, item.raw_description, item.vision_ocr_text, tags, item.found_location])
    )
    try:
        attrs = await azure_openai_service.extract_structured_attributes(text)
    except Exception:
        logger.exception("AI attribute extraction failed; using local fallback", extra={"event": "ai_extract_fallback"})
        attrs = azure_openai_service.fallback_extract_structured_attributes(text)
    try:
        item.ai_clean_description = await azure_openai_service.clean_item_description(item.raw_description)
    except Exception:
        logger.exception("AI description cleaning failed; using raw description", extra={"event": "ai_clean_fallback"})
        item.ai_clean_description = " ".join((item.raw_description or "").split())
    item.ai_extracted_attributes_json = attrs
    item.category = item.category or attrs.get("item_type")
    item.brand = item.brand or attrs.get("brand")
    item.model = item.model or attrs.get("model")
    item.color = item.color or attrs.get("color")
    try:
        item.embedding_vector_id, _ = await azure_openai_service.generate_embedding(text)
    except Exception:
        logger.exception("AI embedding failed; using local fallback vector id", extra={"event": "ai_embedding_fallback"})
        item.embedding_vector_id, _ = azure_openai_service.fallback_embedding(text)
    db.flush()
    try:
        item.search_document_id = await azure_search_service.index_found_item(item)
    except Exception:
        logger.exception("Azure Search indexing failed for found item", extra={"event": "search_index_fallback"})
    db.add(item)
    return item


async def upsert_match_candidate(
    db: Session,
    lost: LostReport,
    found: FoundItem,
    azure_search_score: float,
) -> MatchCandidate | None:
    breakdown = matching_engine.score(lost, found, azure_search_score)
    confidence = breakdown["confidence_level"]
    if confidence is None:
        return None
    try:
        summary = await azure_openai_service.summarize_match_evidence(
            lost.raw_description,
            found.raw_description,
            breakdown,
        )
    except Exception:
        logger.exception("AI match summary failed; using deterministic summary", extra={"event": "ai_summary_fallback"})
        summary = (
            f"Candidate scored {breakdown['match_score']:.1f}/100 from category, text, color, "
            "location, time, flight, and identifier signals. Staff manual approval is required."
        )
    candidate = _get_match_candidate(db, lost.id, found.id)
    is_new_candidate = candidate is None
    if is_new_candidate:
        candidate = MatchCandidate(lost_report_id=lost.id, found_item_id=found.id)
    candidate.match_score = breakdown["match_score"]
    candidate.azure_search_score = breakdown["azure_search_score"]
    candidate.category_score = breakdown["category_score"]
    candidate.text_score = breakdown["text_score"]
    candidate.color_score = breakdown["color_score"]
    candidate.location_score = breakdown["location_score"]
    candidate.time_score = breakdown["time_score"]
    candidate.flight_score = breakdown["flight_score"]
    candidate.unique_identifier_score = breakdown["unique_identifier_score"]
    candidate.confidence_level = confidence
    candidate.ai_match_summary = summary
    if is_new_candidate:
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
        except IntegrityError:
            logger.info(
                "match candidate already existed during upsert",
                extra={"event": "match_candidate_upsert_race", "lost_report_id": lost.id, "found_item_id": found.id},
            )
            candidate = _get_match_candidate(db, lost.id, found.id)
            if candidate is None:
                raise
            _apply_match_breakdown(candidate, breakdown, confidence, summary)
            db.add(candidate)
            db.flush()
    else:
        db.add(candidate)
        db.flush()
    enqueue_outbox(
        db,
        "match_candidate.upserted",
        "match_candidate",
        candidate.id,
        {"lost_report_id": lost.id, "found_item_id": found.id, "match_score": candidate.match_score, "confidence_level": confidence.value},
    )
    logger.info(
        "match candidate scored",
        extra={
            "event": "match_outcome",
            "match_score": candidate.match_score,
            "confidence_level": confidence.value,
        },
    )
    lost.status = LostReportStatus.matched
    found.status = FoundItemStatus.matched
    return candidate


def _get_match_candidate(db: Session, lost_report_id: int, found_item_id: int) -> MatchCandidate | None:
    with db.no_autoflush:
        return (
            db.query(MatchCandidate)
            .filter(MatchCandidate.lost_report_id == lost_report_id, MatchCandidate.found_item_id == found_item_id)
            .one_or_none()
        )


def _apply_match_breakdown(
    candidate: MatchCandidate,
    breakdown: dict,
    confidence: ConfidenceLevel,
    summary: str,
) -> None:
    candidate.match_score = breakdown["match_score"]
    candidate.azure_search_score = breakdown["azure_search_score"]
    candidate.category_score = breakdown["category_score"]
    candidate.text_score = breakdown["text_score"]
    candidate.color_score = breakdown["color_score"]
    candidate.location_score = breakdown["location_score"]
    candidate.time_score = breakdown["time_score"]
    candidate.flight_score = breakdown["flight_score"]
    candidate.unique_identifier_score = breakdown["unique_identifier_score"]
    candidate.confidence_level = confidence
    candidate.ai_match_summary = summary


async def run_matching_for_lost_report(db: Session, report: LostReport) -> list[MatchCandidate]:
    try:
        search_results = await azure_search_service.hybrid_search_found_items(db, report)
    except Exception:
        logger.exception("Azure Search failed while matching lost report", extra={"event": "search_match_fallback"})
        search_results = []
    candidates = []
    for item, search_score in search_results:
        candidate = await upsert_match_candidate(db, report, item, search_score)
        if candidate:
            candidates.append(candidate)
    db.commit()
    for candidate in candidates:
        db.refresh(candidate)
    await invalidate_operational_caches()
    return candidates


async def run_matching_for_found_item(db: Session, item: FoundItem) -> list[MatchCandidate]:
    try:
        search_results = await azure_search_service.hybrid_search_lost_reports(db, item)
    except Exception:
        logger.exception("Azure Search failed while matching found item", extra={"event": "search_match_fallback"})
        search_results = []
    candidates = []
    for report, search_score in search_results:
        candidate = await upsert_match_candidate(db, report, item, search_score)
        if candidate:
            candidates.append(candidate)
    db.commit()
    for candidate in candidates:
        db.refresh(candidate)
    await invalidate_operational_caches()
    return candidates


def confidence_label(score: float) -> ConfidenceLevel | None:
    return matching_engine.confidence_for_score(score)


def add_custody_event(
    db: Session,
    item: FoundItem,
    action: CustodyAction,
    staff_id: int | None,
    location: str | None,
    notes: str | None,
) -> CustodyEvent:
    event = CustodyEvent(
        found_item_id=item.id,
        action=action,
        staff_id=staff_id,
        location=location,
        notes=notes,
    )
    db.add(event)
    return event
