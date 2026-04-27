from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.idempotency import find_idempotent_response, request_hash, store_idempotent_response
from app.models import Base, IdempotencyKey


def test_idempotency_replays_matching_request() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[IdempotencyKey.__table__])
    with Session(engine, expire_on_commit=False) as db:
        hash_value = request_hash({"a": 1})
        store_idempotent_response(db, "scope", "key-1", hash_value, {"id": 10})
        db.commit()

        response = find_idempotent_response(db, "scope", "key-1", hash_value)

    assert response == {"id": 10}


def test_idempotency_rejects_reused_key_with_different_body() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[IdempotencyKey.__table__])
    with Session(engine, expire_on_commit=False) as db:
        store_idempotent_response(db, "scope", "key-1", request_hash({"a": 1}), {"id": 10})
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            find_idempotent_response(db, "scope", "key-1", request_hash({"a": 2}))

    assert exc_info.value.status_code == 409


def test_idempotency_discards_expired_records() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[IdempotencyKey.__table__])
    with Session(engine, expire_on_commit=False) as db:
        record = IdempotencyKey(
            scope="scope",
            key="expired",
            request_hash=request_hash({"a": 1}),
            response_json={"id": 10},
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(record)
        db.commit()

        response = find_idempotent_response(db, "scope", "expired", record.request_hash)

    assert response is None
