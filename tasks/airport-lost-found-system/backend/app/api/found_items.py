from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.utils import (
    add_custody_event,
    enrich_found_item,
    invalidate_operational_caches,
    run_matching_for_found_item,
)
from app.core.database import get_db
from app.core.idempotency import find_idempotent_response, get_idempotency_key, request_hash, store_idempotent_response
from app.core.rbac import require_staff
from app.models import CustodyAction, FoundItem, User
from app.schemas import FoundItemCreate, FoundItemRead, FoundItemUpdate, MatchCandidateRead
from app.services.audit_service import log_audit_event
from app.services.azure_search_service import azure_search_service
from app.services.outbox_service import enqueue_job, enqueue_outbox


router = APIRouter(prefix="/found-items", tags=["found items"])


@router.post("", response_model=FoundItemRead)
async def create_found_item(
    payload: FoundItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> FoundItem:
    idempotency_key = get_idempotency_key(request)
    hash_value = request_hash({"payload": payload.model_dump(mode="json"), "staff_id": current_user.id})
    cached = find_idempotent_response(db, "found_item.create", idempotency_key, hash_value)
    if cached and cached.get("found_item_id"):
        item = db.get(FoundItem, cached["found_item_id"])
        if item:
            return item

    item = FoundItem(**payload.model_dump(), created_by_staff_id=current_user.id)
    db.add(item)
    await enrich_found_item(db, item)
    db.commit()
    db.refresh(item)
    add_custody_event(db, item, CustodyAction.found, current_user.id, item.found_location, "Item registered")
    log_audit_event(
        db,
        action="found_item.created",
        entity_type="found_item",
        entity_id=item.id,
        actor=current_user,
        metadata={"risk_level": item.risk_level.value, "category": item.category},
        request=request,
    )
    enqueue_outbox(db, "found_item.created", "found_item", item.id, {"category": item.category, "risk_level": item.risk_level.value})
    enqueue_job(db, "graph.summary.generate", {"entity_type": "found_item", "entity_id": item.id})
    enqueue_job(db, "matching.found_item", {"found_item_id": item.id})
    store_idempotent_response(db, "found_item.create", idempotency_key, hash_value, {"found_item_id": item.id}, status.HTTP_201_CREATED)
    db.commit()
    await invalidate_operational_caches()
    return item


@router.get("", response_model=list[FoundItemRead])
def list_found_items(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[FoundItem]:
    query = db.query(FoundItem)
    if status_filter:
        query = query.filter(FoundItem.status == status_filter)
    if category:
        query = query.filter(FoundItem.category == category)
    return query.order_by(FoundItem.created_at.desc()).all()


@router.get("/{item_id}", response_model=FoundItemRead)
def get_found_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> FoundItem:
    item = db.get(FoundItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")
    return item


@router.put("/{item_id}", response_model=FoundItemRead)
async def update_found_item(
    item_id: int,
    payload: FoundItemUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> FoundItem:
    item = db.get(FoundItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await enrich_found_item(db, item)
    db.commit()
    db.refresh(item)
    await invalidate_operational_caches()
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_found_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> None:
    item = db.get(FoundItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")
    if item.search_document_id:
        await azure_search_service.delete_document(item.search_document_id)
    db.delete(item)
    db.commit()
    await invalidate_operational_caches()


@router.post("/{item_id}/run-matching", response_model=list[MatchCandidateRead])
async def run_matching(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list:
    item = db.get(FoundItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")
    return await run_matching_for_found_item(db, item)
