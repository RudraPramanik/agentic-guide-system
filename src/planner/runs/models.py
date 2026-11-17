"""Planner run SQLAlchemy model. Persistence only; no status machine."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, TimestampMixin, UUIDMixin


class RunStatus(str, enum.Enum):
    ACCEPTED = "accepted"
    RESOLVING = "resolving"
    RESEARCHING = "researching"
    PLANNING = "planning"
    VALIDATING = "validating"
    COMPLETED = "completed"
    PARTIAL = "partial"
    DEGRADED = "degraded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


def _run_status_values(enum_cls: type[RunStatus]) -> list[str]:
    return [member.value for member in enum_cls]


TERMINAL_RUN_STATUSES = frozenset(
    {
        RunStatus.COMPLETED,
        RunStatus.PARTIAL,
        RunStatus.DEGRADED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
        RunStatus.TIMED_OUT,
    }
)


class PlannerRun(Base, UUIDMixin, TimestampMixin):
    """One generate attempt. ``id`` is the run id. Not soft-deleted."""

    __tablename__ = "planner_runs"

    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(
            RunStatus,
            name="run_status",
            values_callable=_run_status_values,
        ),
        default=RunStatus.ACCEPTED,
        server_default=text("'accepted'"),
        nullable=False,
    )
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="SET NULL"),
        nullable=True,
    )
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fallback_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "idempotency_key",
            name="uq_planner_runs_session_key",
        ),
        Index(
            "uq_planner_runs_user_key",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        CheckConstraint(
            "session_id <> ''",
            name="ck_planner_runs_session_id_nonempty",
        ),
        CheckConstraint(
            "idempotency_key <> ''",
            name="ck_planner_runs_idempotency_key_nonempty",
        ),
    )

    def __repr__(self) -> str:
        return f"<PlannerRun id={self.id} status={self.status}>"
