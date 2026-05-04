"""user notification prefs + worker lease + lost report ip

Revision ID: 0005_user_prefs_and_worker_lease
Revises: 0004_evidence_spans
Create Date: 2026-05-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0005_user_prefs_and_worker_lease"
down_revision: Union[str, None] = "0004_evidence_spans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_if_missing(inspector, table: str, column: sa.Column) -> None:
    if table not in set(inspector.get_table_names()):
        return
    existing = {column_info["name"] for column_info in inspector.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    _add_if_missing(inspector, "users", sa.Column("preferred_channel", sa.String(length=16), nullable=False, server_default="email"))
    _add_if_missing(inspector, "users", sa.Column("preferred_language", sa.String(length=8), nullable=False, server_default="en"))
    _add_if_missing(inspector, "users", sa.Column("notification_consent_at", sa.DateTime(timezone=True), nullable=True))
    _add_if_missing(inspector, "lost_reports", sa.Column("created_from_ip", sa.String(length=80), nullable=True))
    _add_if_missing(inspector, "outbox_events", sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True))
    _add_if_missing(inspector, "background_jobs", sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for table, column in (
        ("background_jobs", "leased_until"),
        ("outbox_events", "leased_until"),
        ("lost_reports", "created_from_ip"),
        ("users", "notification_consent_at"),
        ("users", "preferred_language"),
        ("users", "preferred_channel"),
    ):
        if table not in set(inspector.get_table_names()):
            continue
        existing = {column_info["name"] for column_info in inspector.get_columns(table)}
        if column in existing:
            op.drop_column(table, column)
