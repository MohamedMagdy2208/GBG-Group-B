from datetime import UTC, datetime, timedelta
import hashlib
import secrets
import re
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SENSITIVE_PATTERNS = [
    re.compile(r"\b(?=[A-Z0-9]{6,18}\b)(?=.*\d)[A-Z0-9]+\b"),
    re.compile(r"\b\d{7,16}\b"),
    re.compile(r"\+?\d[\d\s().-]{7,}\d"),
]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def mask_sensitive_text(value: str | None) -> str | None:
    if value is None:
        return None
    masked = value
    for pattern in SENSITIVE_PATTERNS:
        masked = pattern.sub("[REDACTED]", masked)
    return masked


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)
    if len(digits) <= 4:
        return "****"
    return f"***-***-{digits[-4:]}"


def generate_secure_token(byte_count: int = 32) -> str:
    return secrets.token_urlsafe(byte_count)


def hash_token(token: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{settings.jwt_secret}:{token}".encode("utf-8")).hexdigest()


def validate_password_strength(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    checks = [
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    ]
    if sum(checks) < 3:
        raise ValueError("Password must include at least three of lowercase, uppercase, number, and symbol")


def verify_mfa_code(code: str | None, secret_hash: str | None) -> bool:
    if not secret_hash:
        return True
    if not code:
        return False
    # Pilot hook: production can replace this with TOTP/WebAuthn without changing API shape.
    return hash_token(code) == secret_hash
