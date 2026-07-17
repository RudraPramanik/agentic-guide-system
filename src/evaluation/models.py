"""Evaluation domain SQLAlchemy models."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, TimestampMixin, UUIDMixin


class TripEvaluation(Base, UUIDMixin, TimestampMixin):
    """Append-only quality and observability record for each planner generation."""

    __tablename__ = "trip_evaluations"

    # ── Linkage ──
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    destination_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Input ──
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # ── Pipeline counts ──
    candidates_retrieved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidates_after_ranking: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Output snapshot ──
    final_route: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    places_per_day: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    base_lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    base_lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Performance ──
    generation_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_usage: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    llm_model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    llm_retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Agent loop signals ──
    tool_loop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_trace: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    agent_phase_reached: Mapped[str] = mapped_column(
        String(50), default="discover", nullable=False
    )
    readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Resilience signals ──
    used_geo_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_osrm_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    abort_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Quality signals (written after user interaction) ──
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    user_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_trip_eval_dest_created", "destination_id", "created_at"),
        Index("ix_trip_eval_abort", "abort_triggered"),
    )

    def __repr__(self) -> str:
        return f"<TripEvaluation id={self.id} abort={self.abort_triggered}>"
