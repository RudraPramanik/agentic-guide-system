"""Trip domain Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2.shape import to_shape
from pydantic import BaseModel, ConfigDict, Field

from src.trips.models import Trip, TripPlace, TripStatus


class TripPlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    place_id: uuid.UUID
    day_number: int
    order_in_day: int
    travel_time_min: int
    visit_duration_min: int
    suggested_start_time: str | None = None
    arrival_note: str | None = None
    polyline: str | None = None
    name: str | None = None
    lat: float | None = None
    lng: float | None = None

    @classmethod
    def from_trip_place(cls, trip_place: TripPlace) -> TripPlaceOut:
        name: str | None = None
        lat: float | None = None
        lng: float | None = None
        place = getattr(trip_place, "place", None)
        if place is not None:
            name = place.name
            point = to_shape(place.location)
            lat = float(point.y)
            lng = float(point.x)
        return cls(
            id=trip_place.id,
            place_id=trip_place.place_id,
            day_number=trip_place.day_number,
            order_in_day=trip_place.order_in_day,
            travel_time_min=trip_place.travel_time_min,
            visit_duration_min=trip_place.visit_duration_min,
            suggested_start_time=trip_place.suggested_start_time,
            arrival_note=trip_place.arrival_note,
            polyline=trip_place.polyline,
            name=name,
            lat=lat,
            lng=lng,
        )


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    session_id: str
    destination_id: uuid.UUID
    days: int
    preferences: dict = Field(default_factory=dict)
    status: TripStatus
    created_at: datetime
    updated_at: datetime
    places: list[TripPlaceOut] = Field(default_factory=list)

    @classmethod
    def from_trip(cls, trip: Trip) -> TripOut:
        places = [
            TripPlaceOut.from_trip_place(tp)
            for tp in (getattr(trip, "places", None) or [])
        ]
        return cls(
            id=trip.id,
            user_id=trip.user_id,
            session_id=trip.session_id,
            destination_id=trip.destination_id,
            days=trip.days,
            preferences=trip.preferences or {},
            status=trip.status,
            created_at=trip.created_at,
            updated_at=trip.updated_at,
            places=places,
        )
