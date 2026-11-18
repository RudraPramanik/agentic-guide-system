"""add trips discovery_anchor and search_area

Revision ID: c9f2d3e45a61
Revises: b8e1c2d34f50
Create Date: 2026-11-17 18:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c9f2d3e45a61"
down_revision: Union[str, Sequence[str], None] = "b8e1c2d34f50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Additive nullable JSONB columns for location V2 traceability."""
    op.add_column(
        "trips",
        sa.Column(
            "discovery_anchor",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "trips",
        sa.Column(
            "search_area",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop only the two columns added in upgrade."""
    op.drop_column("trips", "search_area")
    op.drop_column("trips", "discovery_anchor")
