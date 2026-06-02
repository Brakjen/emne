"""add find status

Revision ID: 002
Revises: 001
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE find_status AS ENUM ('watching', 'collected', 'passed')")
    op.add_column(
        "finds",
        sa.Column("status", sa.Enum("watching", "collected", "passed", name="find_status"),
                  server_default="watching", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("finds", "status")
    op.execute("DROP TYPE find_status")
