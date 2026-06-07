"""add species

Revision ID: 003
Revises: 002
Create Date: 2026-06-07
"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Common Norwegian (bokmål) names for trees/plants used in bonsai/yamadori.
SEED_SPECIES = [
    "Bjørk", "Dunbjørk", "Hengebjørk", "Or", "Gråor", "Svartor",
    "Selje", "Vier", "Osp", "Eik", "Bøk", "Alm", "Ask", "Lind",
    "Lønn", "Spisslønn", "Platanlønn", "Hassel", "Rogn", "Hegg",
    "Villeple", "Slåpetorn", "Hagtorn", "Einer", "Gran", "Furu",
    "Barlind", "Kristtorn", "Røsslyng", "Blåbær", "Tyttebær",
    "Krekling", "Bjørnebær", "Nype", "Kornell", "Berberis",
    "Syrin", "Tindved", "Pil", "Gråselje", "Dvergbjørk",
]


def upgrade() -> None:
    op.create_table(
        "species",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("name_normalized", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_species_name_normalized", "species", ["name_normalized"], unique=True)

    op.add_column(
        "finds",
        sa.Column("species_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_finds_species_id",
        "finds",
        "species",
        ["species_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_finds_species_id", "finds", ["species_id"])

    # Seed common species
    species_table = sa.table(
        "species",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("name_normalized", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    seen: set[str] = set()
    rows = []
    for name in SEED_SPECIES:
        normalized = " ".join(name.strip().lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append({
            "id": uuid.uuid4(),
            "name": name,
            "name_normalized": normalized,
            "created_at": now,
        })
    if rows:
        op.bulk_insert(species_table, rows)


def downgrade() -> None:
    op.drop_index("idx_finds_species_id", table_name="finds")
    op.drop_constraint("fk_finds_species_id", "finds", type_="foreignkey")
    op.drop_column("finds", "species_id")
    op.drop_index("idx_species_name_normalized", table_name="species")
    op.drop_table("species")
