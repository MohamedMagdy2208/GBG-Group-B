from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.rbac import get_current_user
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_mfa_code,
    verify_password,
)
from app.models import AuditSeverity, PasswordResetToken, RefreshToken, User, UserRole
from app.schemas import (
    LoginRequest,
    LogoutRequest,
    MFAVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, dependencies=[Depends(rate_limit("auth_register", 20, 60))])
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    _validate_password(payload.password)
    existing = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=UserRole.passenger,
    )
    db.add(user)
    db.flush()
    log_audit_event(db, action="auth.registered", entity_type="user", entity_id=user.id, actor=user, request=request)
    response = _issue_tokens(db, user, request)
    db.commit()
    db.refresh(user)
    return response


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("auth_login", get_settings().rate_limit_login_per_minute, 60))])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    now = datetime.now(UTC)
    user = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.is_disabled:
        log_audit_event(db, action="auth.login_disabled", entity_type="user", entity_id=user.id, actor=user, severity=AuditSeverity.warning, request=request)
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="User account is temporarily locked")
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.account_lockout_threshold:
            user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
            log_audit_event(db, action="auth.account_locked", entity_type="user", entity_id=user.id, actor=user, severity=AuditSeverity.warning, request=request)
        else:
            log_audit_event(db, action="auth.login_failed", entity_type="user", entity_id=user.id, actor=user, severity=AuditSeverity.warning, request=request)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.mfa_enabled and (not user.mfa_secret_hash or not verify_mfa_code(payload.mfa_code, user.mfa_secret_hash)):
        log_audit_event(db, action="auth.mfa_failed", entity_type="user", entity_id=user.id, actor=user, severity=AuditSeverity.warning, request=request)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA verification required")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    log_audit_event(db, action="auth.login_succeeded", entity_type="user", entity_id=user.id, actor=user, request=request)
    response = _issue_tokens(db, user, request)
    db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(rate_limit("auth_refresh", 30, 60))])
def refresh_token(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    now = datetime.now(UTC)
    token_hash = hash_token(payload.refresh_token)
    token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).one_or_none()
    if not token or token.revoked_at or token.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = db.get(User, token.user_id)
    if not user or user.is_disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    token.revoked_at = now
    log_audit_event(db, action="auth.token_refreshed", entity_type="user", entity_id=user.id, actor=user, request=request)
    response = _issue_tokens(db, user, request)
    db.commit()
    return response


@router.post("/logout")
def logout(payload: LogoutRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, str]:
    if payload.refresh_token:
        token = db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(payload.refresh_token)).one_or_none()
        if token and token.user_id == current_user.id:
            token.revoked_at = datetime.now(UTC)
    log_audit_event(db, action="auth.logout", entity_type="user", entity_id=current_user.id, actor=current_user, request=request)
    db.commit()
    return {"status": "ok"}


@router.post("/password-reset/request", dependencies=[Depends(rate_limit("password_reset", 5, 60))])
def password_reset_request(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    token_value = None
    user = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if user and not user.is_disabled:
        token_value = generate_secure_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(token_value),
                expires_at=datetime.now(UTC) + timedelta(minutes=settings.password_reset_token_expire_minutes),
            )
        )
        log_audit_event(db, action="auth.password_reset_requested", entity_type="user", entity_id=user.id, actor=user, request=request)
        db.commit()
    response = {"status": "ok"}
    if token_value and settings.environment == "local":
        response["local_reset_token"] = token_value
    return response


@router.post("/password-reset/confirm", dependencies=[Depends(rate_limit("password_reset_confirm", 10, 60))])
def password_reset_confirm(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    _validate_password(payload.new_password)
    now = datetime.now(UTC)
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == hash_token(payload.token)).one_or_none()
    if not reset or reset.used_at or reset.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user = db.get(User, reset.user_id)
    if not user or user.is_disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    user.password_hash = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    reset.used_at = now
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)).update({"revoked_at": now})
    log_audit_event(db, action="auth.password_reset_confirmed", entity_type="user", entity_id=user.id, actor=user, severity=AuditSeverity.warning, request=request)
    db.commit()
    return {"status": "ok"}


@router.post("/mfa/verify")
def verify_mfa(payload: MFAVerifyRequest, current_user: User = Depends(get_current_user)) -> dict[str, bool]:
    return {"verified": bool(current_user.mfa_secret_hash and verify_mfa_code(payload.code, current_user.mfa_secret_hash))}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/me/preferences")
def get_preferences(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "preferred_channel": current_user.preferred_channel or "email",
        "preferred_language": current_user.preferred_language or "en",
        "notification_consent_at": current_user.notification_consent_at,
    }


@router.put("/me/preferences")
def set_preferences(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    channel = (payload.get("preferred_channel") or current_user.preferred_channel or "email").lower()
    if channel not in {"email", "sms", "none"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported channel")
    language = (payload.get("preferred_language") or current_user.preferred_language or "en").lower()
    if language not in {"en", "ar"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported language")
    current_user.preferred_channel = channel
    current_user.preferred_language = language
    if payload.get("consent") and current_user.notification_consent_at is None:
        current_user.notification_consent_at = datetime.now(UTC)
    elif payload.get("consent") is False:
        current_user.notification_consent_at = None
    db.commit()
    db.refresh(current_user)
    return {
        "preferred_channel": current_user.preferred_channel,
        "preferred_language": current_user.preferred_language,
        "notification_consent_at": current_user.notification_consent_at,
    }


def _issue_tokens(db: Session, user: User, request: Request) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(str(user.id), {"role": user.role.value})
    refresh_token_value = generate_secure_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token_value),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_value,
        expires_in_seconds=settings.access_token_expire_minutes * 60,
        user=user,
    )


def _validate_password(password: str) -> None:
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
