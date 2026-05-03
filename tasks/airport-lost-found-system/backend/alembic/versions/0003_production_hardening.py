"""production hardening

Revision ID: 0003_production_hardening
Revises: 0002_claims_voice_qr_audit
Create Date: 2026-04-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0003_production_hardening"
down_revision: Union[str, None] = "0002_claims_voice_qr_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "is_disabled" not in user_columns:
            op.add_column("users", sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "failed_login_attempts" not in user_columns:
            op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
        if "locked_until" not in user_columns:
            op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
        if "mfa_enabled" not in user_columns:
            op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "mfa_secret_hash" not in user_columns:
            op.add_column("users", sa.Column("mfa_secret_hash", sa.String(length=255), nullable=True))
        if "last_login_at" not in user_columns:
            op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ip_address", sa.String(length=80), nullable=True),
            sa.Column("user_agent", sa.String(length=300), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
        op.create_index("ix_refresh_tokens_user_revoked", "refresh_tokens", ["user_id", "revoked_at"])

    if "password_reset_tokens" not in tables:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_password_reset_tokens_hash", "password_reset_tokens", ["token_hash"], unique=True)

    if "idempotency_keys" not in tables:
        op.create_table(
            "idempotency_keys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("scope", sa.String(length=120), nullable=False),
            sa.Column("key", sa.String(length=160), nullable=False),
            sa.Column("request_hash", sa.String(length=128), nullable=False),
            sa.Column("response_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status_code", sa.Integer(), nullable=False, server_default="200"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_idempotency_scope_key", "idempotency_keys", ["scope", "key"], unique=True)

    if "outbox_events" not in tables:
        op.create_table(
            "outbox_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("aggregate_type", sa.String(length=80), nullable=False),
            sa.Column("aggregate_id", sa.String(length=80), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_outbox_events_aggregate", "outbox_events", ["aggregate_type", "aggregate_id"])
        op.create_index("ix_outbox_events_status_next", "outbox_events", ["status", "next_attempt_at"])

    if "background_jobs" not in tables:
        op.create_table(
            "background_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("job_type", sa.String(length=120), nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_background_jobs_status_next", "background_jobs", ["status", "next_run_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    for table_name in ("background_jobs", "outbox_events", "idempotency_keys", "password_reset_tokens", "refresh_tokens"):
        if table_name in tables:
            op.drop_table(table_name)

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        for column_name in ("last_login_at", "mfa_secret_hash", "mfa_enabled", "locked_until", "failed_login_attempts", "is_disabled"):
            if column_name in user_columns:
                op.drop_column("users", column_name)
