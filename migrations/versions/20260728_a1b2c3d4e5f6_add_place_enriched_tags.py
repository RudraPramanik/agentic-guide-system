"""add_place_enriched_tags

Revision ID: a1b2c3d4e5f6
Revises: 6e0f01af33c5
Create Date: 2026-07-28 06:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6e0f01af33c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Place.enriched_tags (LLM list) — distinct from raw OSM tags."""
    op.add_column(
        "places",
        sa.Column(
            "enriched_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # Drop server default after backfill so app-side default=list remains the source of truth
    op.alter_column("places", "enriched_tags", server_default=None)


def downgrade() -> None:
    """Remove enriched_tags column."""
    op.drop_column("places", "enriched_tags")
