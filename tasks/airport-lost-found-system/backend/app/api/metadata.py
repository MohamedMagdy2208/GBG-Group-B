from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import require_admin, require_staff
from app.core.security import hash_password, validate_password_strength
from app.models import AirportLocation, AuditSeverity, ItemCategory, User
from app.schemas import (
    AirportLocationCreate,
    AirportLocationRead,
    ItemCategoryCreate,
    ItemCategoryRead,
    UserAdminCreate,
    UserRead,
    UserUpdate,
)
from app.services.audit_service import log_audit_event


router = APIRouter(tags=["metadata"])


@router.get("/locations", response_model=list[AirportLocationRead])
def list_locations(db: Session = Depends(get_db)) -> list[AirportLocation]:
    return db.query(AirportLocation).order_by(AirportLocation.name).all()


@router.post("/locations", response_model=AirportLocationRead)
def create_location(
    payload: AirportLocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AirportLocation:
    location = AirportLocation(**payload.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.get("/categories", response_model=list[ItemCategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[ItemCategory]:
    return db.query(ItemCategory).order_by(ItemCategory.name).all()


@router.post("/categories", response_model=ItemCategoryRead)
def create_category(
    payload: ItemCategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ItemCategory:
    category = ItemCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserRead)
def create_user(
    payload: UserAdminCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    existing = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        phone=payload.phone,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    log_audit_event(db, action="admin.user_created", entity_type="user", entity_id=user.id, actor=current_user, severity=AuditSeverity.warning, request=request)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    log_audit_event(
        db,
        action="admin.user_updated",
        entity_type="user",
        entity_id=user.id,
        actor=current_user,
        severity=AuditSeverity.warning,
        metadata={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        request=request,
    )
    db.commit()
    db.refresh(user)
    return user
