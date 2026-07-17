"""Destination domain SQLAlchemy models."""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base import Base, TimestampMixin, UUIDMixin


class Destination(Base, UUIDMixin, TimestampMixin):
    """Caches Nominatim geocode results and denormalized readiness counters."""

    __tablename__ = "destinations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    osm_place_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Readiness counters — updated by seed/enrich scripts, not by FK aggregates
    place_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enriched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    indexed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Destination id={self.id} name={self.name}>"
