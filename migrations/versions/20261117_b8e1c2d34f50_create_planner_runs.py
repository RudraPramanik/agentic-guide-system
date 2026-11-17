"""create planner_runs

Revision ID: b8e1c2d34f50
Revises: a1b2c3d4e5f6
Create Date: 2026-11-17 07:40:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8e1c2d34f50"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RUN_STATUS_VALUES = (
    "accepted",
    "resolving",
    "researching",
    "planning",
    "validating",
    "completed",
    "partial",
    "degraded",
    "failed",
    "cancelled",
    "timed_out",
)


def upgrade() -> None:
    """Create planner_runs. No changes to existing application tables."""
    status_enum = postgresql.ENUM(*_RUN_STATUS_VALUES, name="run_status")
    status_enum.create(op.get_bind(), checkfirst=False)
    op.create_table(
        "planner_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="run_status", create_type=False),
            server_default=sa.text("'accepted'"),
            nullable=False,
        ),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("trip_id", sa.UUID(), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("workflow_version", sa.String(length=64), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("fallback_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("session_id <> ''", name="ck_planner_runs_session_id_nonempty"),
        sa.CheckConstraint(
            "idempotency_key <> ''",
            name="ck_planner_runs_idempotency_key_nonempty",
        ),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "idempotency_key",
            name="uq_planner_runs_session_key",
        ),
    )
    op.create_index(
        "uq_planner_runs_user_key",
        "planner_runs",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop planner_runs and the run_status enum only."""
    op.drop_index("uq_planner_runs_user_key", table_name="planner_runs")
    op.drop_table("planner_runs")
    postgresql.ENUM(name="run_status").drop(op.get_bind(), checkfirst=False)
