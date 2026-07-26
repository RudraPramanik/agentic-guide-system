"""Place domain Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, ConfigDict

from src.places.models import Place


class PlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    osm_id: str
    name: str
    category: str
    tags: dict
    summary: str | None
    lat: float
    lng: float
    destination_id: uuid.UUID
    created_at: datetime

    @classmethod
    def from_place(cls, place: Place) -> PlaceOut:
        """Use geoalchemy2.shape.to_shape(place.location) → .y=lat, .x=lng."""
        point = to_shape(place.location)
        return cls(
            id=place.id,
            osm_id=place.osm_id,
            name=place.name,
            category=place.category,
            tags=place.tags,
            summary=place.summary,
            lat=point.y,
            lng=point.x,
            destination_id=place.destination_id,
            created_at=place.created_at,
        )
