"""Trips domain SQLAlchemy models."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.places.models import Place


class TripStatus(str, enum.Enum):
    DRAFT = "draft"
    COMPLETE = "complete"
    FAILED = "failed"


class StopStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    SUGGESTED = "suggested"
    REMOVED = "removed"
    USER_ADDED = "user_added"


class GeometryProvenance(str, enum.Enum):
    OSRM = "osrm"
    HAVERSINE_ESTIMATE = "haversine_estimate"
    NONE = "none"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


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
    discovery_anchor: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    search_area: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[TripStatus] = mapped_column(
        SAEnum(TripStatus, name="trip_status"),
        default=TripStatus.DRAFT,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    places: Mapped[list[TripPlace]] = relationship(
        "TripPlace",
        back_populates="trip",
        order_by="TripPlace.day_number, TripPlace.order_in_day",
        cascade="all, delete-orphan",
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
    stop_status: Mapped[StopStatus] = mapped_column(
        SAEnum(
            StopStatus,
            name="stop_status",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=StopStatus.CONFIRMED,
        server_default=StopStatus.CONFIRMED.value,
    )
    geometry_provenance: Mapped[GeometryProvenance | None] = mapped_column(
        SAEnum(
            GeometryProvenance,
            name="geometry_provenance",
            values_callable=_enum_values,
        ),
        nullable=True,
    )

    trip: Mapped[Trip] = relationship("Trip", back_populates="places")
    place: Mapped[Place] = relationship("Place")

    __table_args__ = (
        Index("ix_trip_places_trip_day", "trip_id", "day_number"),
        UniqueConstraint("trip_id", "place_id", name="uq_trip_place"),
    )

    def __repr__(self) -> str:
        return (
            f"<TripPlace trip={self.trip_id} day={self.day_number} "
            f"order={self.order_in_day}>"
        )


class EditType(str, enum.Enum):
    REORDER = "reorder"
    REMOVE_STOP = "remove_stop"
    ADD_STOP = "add_stop"
    REOPTIMIZE_DAY = "reoptimize_day"


class TripEditEvent(Base, UUIDMixin, TimestampMixin):
    """
    Append-only audit record for every user-initiated trip edit.
    Used by evaluation.service.record_edit() to flag user_edited=True
    on the linked TripEvaluation. Never soft-deleted.
    """

    __tablename__ = "trip_edit_events"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edit_type: Mapped[EditType] = mapped_column(
        SAEnum(EditType, name="edit_type"),
        nullable=False,
    )
    day_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_trip_edit_events_trip_created", "trip_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<TripEditEvent id={self.id} trip={self.trip_id} type={self.edit_type}>"
