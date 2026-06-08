"""add app_settings table

Revision ID: 005
Revises: 004
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(length=255), nullable=False, server_default="Rogaland, Norway"),
        sa.Column("ai_species_id", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_review_checklist", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_collect_timing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ai_suggest_metadata", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    # Seed the single default row.
    op.execute(
        "INSERT INTO app_settings (id, region) VALUES (1, 'Rogaland, Norway')"
    )


def downgrade() -> None:
    op.drop_table("app_settings")
