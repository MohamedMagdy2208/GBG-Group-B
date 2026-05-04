"""evidence spans for match candidates

Revision ID: 0004_evidence_spans
Revises: 0003_production_hardening
Create Date: 2026-05-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0004_evidence_spans"
down_revision: Union[str, None] = "0003_production_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "match_candidates" not in tables:
        return
    columns = {column["name"] for column in inspector.get_columns("match_candidates")}
    if "evidence_spans_json" not in columns:
        op.add_column(
            "match_candidates",
            sa.Column("evidence_spans_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "match_candidates" not in tables:
        return
    columns = {column["name"] for column in inspector.get_columns("match_candidates")}
    if "evidence_spans_json" in columns:
        op.drop_column("match_candidates", "evidence_spans_json")
