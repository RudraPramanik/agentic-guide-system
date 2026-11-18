"""add trip version, stop status, and geometry provenance

Revision ID: d0a3e4f56b72
Revises: c9f2d3e45a61
Create Date: 2026-11-18 03:40:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d0a3e4f56b72"
down_revision: Union[str, Sequence[str], None] = "c9f2d3e45a61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STOP_STATUS = postgresql.ENUM(
    "confirmed",
    "suggested",
    "removed",
    "user_added",
    name="stop_status",
    create_type=False,
)
_GEOMETRY_PROVENANCE = postgresql.ENUM(
    "osrm",
    "haversine_estimate",
    "none",
    name="geometry_provenance",
    create_type=False,
)


def upgrade() -> None:
    """Additive columns. Existing trips become version 1; existing stops stay confirmed."""
    bind = op.get_bind()
    postgresql.ENUM(
        "confirmed",
        "suggested",
        "removed",
        "user_added",
        name="stop_status",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "osrm",
        "haversine_estimate",
        "none",
        name="geometry_provenance",
    ).create(bind, checkfirst=True)
    op.add_column(
        "trips",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "trip_places",
        sa.Column(
            "stop_status",
            _STOP_STATUS,
            nullable=False,
            server_default="confirmed",
        ),
    )
    op.add_column(
        "trip_places",
        sa.Column(
            "geometry_provenance",
            _GEOMETRY_PROVENANCE,
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop only the columns and enums added in upgrade."""
    op.drop_column("trip_places", "geometry_provenance")
    op.drop_column("trip_places", "stop_status")
    op.drop_column("trips", "version")
    bind = op.get_bind()
    postgresql.ENUM(name="geometry_provenance").drop(bind, checkfirst=True)
    postgresql.ENUM(name="stop_status").drop(bind, checkfirst=True)
