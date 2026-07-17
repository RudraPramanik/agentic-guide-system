"""Places domain SQLAlchemy models."""

import uuid
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Place(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "places"

    osm_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    tags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PostGIS POINT — SRID 4326 = WGS84 (standard GPS coordinates)
    location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    destination_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_places_destination_category", "destination_id", "category"),
    )

    def __repr__(self) -> str:
        return f"<Place id={self.id} name={self.name} category={self.category}>"
