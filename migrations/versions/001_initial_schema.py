"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "finds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "tree", "sapling", "burl", "rock", "mushroom",
                "viewpoint", "deadwood", "other",
                name="find_category",
            ),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "location",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("location_accuracy", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "visits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("find_id", sa.Uuid(), sa.ForeignKey("finds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_visits_find_id", "visits", ["find_id"])

    op.create_table(
        "photos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("find_id", sa.Uuid(), sa.ForeignKey("finds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("visits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("thumbnail_key", sa.String(512), nullable=False),
        sa.Column("caption", sa.String(500), nullable=True),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_photos_find_id", "photos", ["find_id"])
    op.create_index("idx_photos_visit_id", "photos", ["visit_id"])


def downgrade() -> None:
    op.drop_table("photos")
    op.drop_table("visits")
    op.drop_table("finds")
    op.execute("DROP TYPE IF EXISTS find_category")
