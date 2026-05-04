"""perceptual hash and image vector ids on lost reports + found items

Revision ID: 0006_image_similarity
Revises: 0005_user_prefs_and_worker_lease
Create Date: 2026-05-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0006_image_similarity"
down_revision: Union[str, None] = "0005_user_prefs_and_worker_lease"
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
    _add_if_missing(inspector, "found_items", sa.Column("image_phash", sa.String(length=32), nullable=True))
    _add_if_missing(inspector, "found_items", sa.Column("image_vector_id", sa.String(length=120), nullable=True))
    _add_if_missing(inspector, "lost_reports", sa.Column("proof_phash", sa.String(length=32), nullable=True))
    _add_if_missing(inspector, "lost_reports", sa.Column("image_vector_id", sa.String(length=120), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    for table, column in (
        ("lost_reports", "image_vector_id"),
        ("lost_reports", "proof_phash"),
        ("found_items", "image_vector_id"),
        ("found_items", "image_phash"),
    ):
        if table not in set(inspector.get_table_names()):
            continue
        existing = {column_info["name"] for column_info in inspector.get_columns(table)}
        if column in existing:
            op.drop_column(table, column)
