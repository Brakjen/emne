"""add cover_photo_id to finds

Revision ID: 004
Revises: 003
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("finds", sa.Column("cover_photo_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_finds_cover_photo_id",
        "finds",
        "photos",
        ["cover_photo_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_finds_cover_photo_id", "finds", ["cover_photo_id"])


def downgrade() -> None:
    op.drop_index("idx_finds_cover_photo_id", table_name="finds")
    op.drop_constraint("fk_finds_cover_photo_id", "finds", type_="foreignkey")
    op.drop_column("finds", "cover_photo_id")
