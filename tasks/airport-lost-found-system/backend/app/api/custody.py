from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.utils import add_custody_event, invalidate_operational_caches
from app.core.database import get_db
from app.core.rbac import require_staff
from app.models import FoundItem, User
from app.schemas import CustodyEventCreate, CustodyEventRead
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/found-items/{item_id}/custody-events", tags=["custody"])


@router.post("", response_model=CustodyEventRead)
async def create_custody_event(
    item_id: int,
    payload: CustodyEventCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    item = db.get(FoundItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")
    event = add_custody_event(db, item, payload.action, current_user.id, payload.location, payload.notes)
    log_audit_event(
        db,
        action=f"custody.{payload.action.value}",
        entity_type="found_item",
        entity_id=item.id,
        actor=current_user,
        metadata={"location": payload.location},
        request=request,
    )
    db.commit()
    db.refresh(event)
    await invalidate_operational_caches()
    return event


@router.get("", response_model=list[CustodyEventRead])
def list_custody_events(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    item = db.get(FoundItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")
    return sorted(item.custody_events, key=lambda event: event.timestamp)
