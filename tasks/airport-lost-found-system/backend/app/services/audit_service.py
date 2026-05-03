from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.security import mask_sensitive_text
from app.models import AuditLog, AuditSeverity, User


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return mask_sensitive_text(value)
    if isinstance(value, Mapping):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def log_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    actor: User | None = None,
    severity: AuditSeverity = AuditSeverity.info,
    metadata: dict[str, Any] | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_role=actor.role.value if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        severity=severity,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        metadata_json=_redact(metadata or {}),
        before_json=_redact(before or {}),
        after_json=_redact(after or {}),
    )
    db.add(log)
    return log
