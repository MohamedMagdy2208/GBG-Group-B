from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.utils import add_custody_event, invalidate_operational_caches
from app.core.database import get_db
from app.core.rbac import require_staff
from app.models import AuditSeverity, BarcodeLabel, BarcodeLabelStatus, CustodyAction, FoundItem, User
from app.schemas import BarcodeLabelRead, LabelScanRequest, LabelScanResponse
from app.services.audit_service import log_audit_event
from app.services.label_service import label_service


router = APIRouter(tags=["labels"])


@router.post("/found-items/{item_id}/labels", response_model=BarcodeLabelRead)
async def create_found_item_label(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> BarcodeLabel:
    item = db.get(FoundItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found")
    existing = (
        db.query(BarcodeLabel)
        .filter(
            BarcodeLabel.entity_type == "found_item",
            BarcodeLabel.entity_id == item.id,
            BarcodeLabel.status == BarcodeLabelStatus.active,
        )
        .one_or_none()
    )
    if existing:
        return existing
    label = label_service.create_found_item_label(item, current_user)
    db.add(label)
    log_audit_event(
        db,
        action="label.created",
        entity_type="found_item",
        entity_id=item.id,
        actor=current_user,
        metadata={"label_code": label.label_code},
        request=request,
    )
    db.commit()
    db.refresh(label)
    return label


@router.post("/labels/scan", response_model=LabelScanResponse)
async def scan_label(
    payload: LabelScanRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    code = _extract_code(payload.label_code)
    label = db.query(BarcodeLabel).filter(BarcodeLabel.label_code == code).one_or_none()
    if not label or label.status != BarcodeLabelStatus.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active label not found")
    item = db.get(FoundItem, label.entity_id) if label.entity_type == "found_item" else None
    now = datetime.now(UTC)
    db.execute(
        update(BarcodeLabel)
        .where(BarcodeLabel.id == label.id)
        .values(scan_count=BarcodeLabel.scan_count + 1, last_scanned_at=now)
    )
    db.refresh(label)
    event = None
    if item:
        event = add_custody_event(
            db,
            item,
            CustodyAction.note,
            current_user.id,
            payload.location or item.storage_location,
            payload.notes or f"QR label {label.label_code} scanned",
        )
    log_audit_event(
        db,
        action="label.scanned",
        entity_type=label.entity_type,
        entity_id=label.entity_id,
        actor=current_user,
        severity=AuditSeverity.info,
        metadata={"label_code": label.label_code, "location": payload.location},
        request=request,
    )
    db.commit()
    db.refresh(label)
    if event:
        db.refresh(event)
    await invalidate_operational_caches()
    return {"label": label, "found_item": item, "custody_event": event}


@router.get("/labels/{label_code}", response_model=LabelScanResponse)
def get_label(
    label_code: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    label = db.query(BarcodeLabel).filter(BarcodeLabel.label_code == label_code).one_or_none()
    if not label:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    item = db.get(FoundItem, label.entity_id) if label.entity_type == "found_item" else None
    return {"label": label, "found_item": item, "custody_event": None}


@router.get("/labels/{label_code}/qr")
def label_qr(label_code: str, db: Session = Depends(get_db)) -> Response:
    label = db.query(BarcodeLabel).filter(BarcodeLabel.label_code == label_code).one_or_none()
    if not label:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")
    return Response(
        content=label_service.qr_svg(label.qr_payload, label.label_code),
        media_type="image/svg+xml",
        headers={"Cache-Control": "private, max-age=60"},
    )


def _extract_code(value: str) -> str:
    if "code=" in value:
        return value.rsplit("code=", 1)[-1].split("&", 1)[0]
    return value.strip()
