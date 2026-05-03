from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_staff
from app.models import Notification, User
from app.schemas import NotificationRead, NotificationSendRequest
from app.services.notification_service import notification_service


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send-match-alert", response_model=NotificationRead)
async def send_match_alert(
    payload: NotificationSendRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> Notification:
    notification = Notification(**payload.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return await notification_service.send_notification(db, notification)


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[Notification]:
    return db.query(Notification).order_by(Notification.created_at.desc()).all()
