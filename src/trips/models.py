"""Trips domain SQLAlchemy models."""

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class TripStatus(str, enum.Enum):
    DRAFT = "draft"
    COMPLETE = "complete"
    FAILED = "failed"


class Trip(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "trips"

    # One of user_id or session_id always identifies the owner
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    destination_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[TripStatus] = mapped_column(
        SAEnum(TripStatus, name="trip_status"),
        default=TripStatus.DRAFT,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_trips_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Trip id={self.id} status={self.status} days={self.days}>"


class TripPlace(Base, UUIDMixin, TimestampMixin):
    """One row per stop per day in a trip. No SoftDeleteMixin — stops are hard-deleted."""

    __tablename__ = "trip_places"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("places.id", ondelete="RESTRICT"),
        nullable=False,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    order_in_day: Mapped[int] = mapped_column(Integer, nullable=False)
    travel_time_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    visit_duration_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    suggested_start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    arrival_note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    polyline: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_trip_places_trip_day", "trip_id", "day_number"),
        UniqueConstraint("trip_id", "place_id", name="uq_trip_place"),
    )

    def __repr__(self) -> str:
        return (
            f"<TripPlace trip={self.trip_id} day={self.day_number} "
            f"order={self.order_in_day}>"
        )
