from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.models import IdempotencyKey


IDEMPOTENCY_HEADER = "Idempotency-Key"


def get_idempotency_key(request: Request) -> str | None:
    value = request.headers.get(IDEMPOTENCY_HEADER)
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > 160:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key is too long")
    return value


def request_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def find_idempotent_response(db: Session, scope: str, key: str | None, request_hash_value: str) -> dict[str, Any] | None:
    if not key:
        return None
    record = db.query(IdempotencyKey).filter(IdempotencyKey.scope == scope, IdempotencyKey.key == key).one_or_none()
    if not record:
        return None
    if record.request_hash != request_hash_value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency-Key was reused with a different request body")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        db.delete(record)
        db.flush()
        return None
    return record.response_json or {}


def store_idempotent_response(
    db: Session,
    scope: str,
    key: str | None,
    request_hash_value: str,
    response_json: dict[str, Any],
    status_code: int = 200,
    ttl_hours: int = 24,
) -> None:
    if not key:
        return
    db.add(
        IdempotencyKey(
            scope=scope,
            key=key,
            request_hash=request_hash_value,
            response_json=response_json,
            status_code=status_code,
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        )
    )
