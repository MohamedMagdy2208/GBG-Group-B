"""claims voice qr audit

Revision ID: 0002_claims_voice_qr_audit
Revises: 0001_initial_schema
Create Date: 2026-04-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from app.models import AuditLog, BarcodeLabel, ClaimVerification


revision: str = "0002_claims_voice_qr_audit"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "claim_verifications" not in inspector.get_table_names():
        ClaimVerification.__table__.create(bind, checkfirst=True)
    if "barcode_labels" not in inspector.get_table_names():
        BarcodeLabel.__table__.create(bind, checkfirst=True)
    if "audit_logs" not in inspector.get_table_names():
        AuditLog.__table__.create(bind, checkfirst=True)

    chat_columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
    if "language" not in chat_columns:
        op.add_column("chat_sessions", sa.Column("language", sa.String(length=12), nullable=False, server_default="en"))
    if "voice_enabled" not in chat_columns:
        op.add_column("chat_sessions", sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    chat_columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
    if "voice_enabled" in chat_columns:
        op.drop_column("chat_sessions", "voice_enabled")
    if "language" in chat_columns:
        op.drop_column("chat_sessions", "language")

    for table_name in ("audit_logs", "barcode_labels", "claim_verifications"):
        if table_name in inspector.get_table_names():
            op.drop_table(table_name)
