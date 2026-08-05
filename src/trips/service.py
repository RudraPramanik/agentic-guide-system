"""Trip service — save_from_state UoW, ownership, claim, GeoJSON, HTTP helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PageParams
from src.trips.exceptions import (
    TripAlreadyClaimedError,
    TripForbiddenError,
    TripNotFoundError,
)
from src.trips.models import Trip, TripStatus
from src.trips.polyline import decode_polyline
from src.trips.repository import TripRepository


def _as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _trip_status(state: dict[str, Any]) -> TripStatus:
    if state.get("plan_complete") and not state.get("abort_triggered"):
        return TripStatus.COMPLETE
    if state.get("abort_triggered"):
        return TripStatus.FAILED
    return TripStatus.DRAFT


def _schedule_usable(schedule: Any) -> bool:
    if not isinstance(schedule, list) or not schedule:
        return False
    for day in schedule:
        if not isinstance(day, dict):
            continue
        stops = day.get("stops") or []
        if isinstance(stops, list) and len(stops) > 0:
            return True
    return False


def _concat_day_coords(
    leg_coords: list[list[tuple[float, float]]],
) -> list[list[float]]:
    """Merge leg (lat,lng) lists into GeoJSON [lng,lat] ring, deduping shared endpoints."""
    merged: list[list[float]] = []
    for coords in leg_coords:
        for lat, lng in coords:
            point = [lng, lat]
            if merged and merged[-1] == point:
                continue
            merged.append(point)
    return merged


class TripService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TripRepository(session)

    async def save_from_state(
        self,
        state: dict[str, Any],
        user_id: UUID | None,
        session_id: str,
    ) -> Trip | None:
        """
        Persist Trip + TripPlace rows in one transaction (UoW).
        Returns None when there is nothing usable to save (empty / clarification-only).
        """
        schedule = state.get("schedule") or []
        if not _schedule_usable(schedule):
            return None

        destination_id = _as_uuid(state["destination_id"])
        preferences = {
            "interests": state.get("interests") or [],
            "budget": state.get("budget"),
            "include_offbeat": state.get("include_offbeat"),
            "include_trekking": state.get("include_trekking"),
        }
        status = _trip_status(state)

        place_rows: list[dict[str, Any]] = []
        for day in schedule:
            if not isinstance(day, dict):
                continue
            day_number = int(day.get("day") or 0)
            stops = day.get("stops") or []
            if not isinstance(stops, list):
                continue
            for stop in stops:
                if not isinstance(stop, dict):
                    continue
                place_rows.append(
                    {
                        "place_id": _as_uuid(stop["place_id"]),
                        "day_number": day_number,
                        "order_in_day": int(stop.get("order") or 0),
                        "travel_time_min": int(stop.get("travel_time_min") or 0),
                        "visit_duration_min": int(stop.get("visit_duration_min") or 60),
                        "suggested_start_time": stop.get("suggested_start_time"),
                        "arrival_note": stop.get("arrival_note"),
                        "polyline": stop.get("leg_polyline"),
                    }
                )

        if not place_rows:
            return None

        try:
            trip = await self.repo.create(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "destination_id": destination_id,
                    "days": len(schedule),
                    "preferences": preferences,
                    "status": status,
                }
            )
            for row in place_rows:
                row["trip_id"] = trip.id
            await self.repo.create_trip_places(place_rows)
            await self.session.commit()
            await self.session.refresh(trip)
            return trip
        except Exception:
            await self.session.rollback()
            raise

    def assert_can_access(
        self,
        trip: Trip,
        *,
        user_id: UUID | None,
        session_id: str | None,
    ) -> None:
        """Raise TripForbiddenError if caller may not access this trip."""
        if user_id is None:
            if not session_id or session_id != trip.session_id:
                raise TripForbiddenError()
            return

        if trip.user_id == user_id:
            return
        if trip.user_id is None and session_id and session_id == trip.session_id:
            return
        raise TripForbiddenError()

    async def claim_for_user(
        self,
        trip: Trip,
        user_id: UUID,
        session_id: str,
    ) -> Trip:
        """Transfer an anonymous trip to an authenticated user (session must match)."""
        if trip.user_id is not None:
            raise TripAlreadyClaimedError(trip_id=str(trip.id))
        if session_id != trip.session_id:
            raise TripForbiddenError()

        trip.user_id = user_id
        await self.session.flush()
        await self.session.commit()
        loaded = await self.repo.get_with_places(trip.id)
        assert loaded is not None
        return loaded

    async def get_for_access(
        self,
        trip_id: UUID,
        *,
        user_id: UUID | None,
        session_id: str | None,
    ) -> Trip:
        """Load trip with places or 404; then enforce ownership (403)."""
        trip = await self.repo.get_with_places(trip_id)
        if trip is None:
            raise TripNotFoundError(trip_id=str(trip_id))
        self.assert_can_access(trip, user_id=user_id, session_id=session_id)
        return trip

    async def get_trip_or_404(self, trip_id: UUID) -> Trip:
        """Load trip with places for public readers (e.g. geojson), or 404."""
        trip = await self.repo.get_with_places(trip_id)
        if trip is None:
            raise TripNotFoundError(trip_id=str(trip_id))
        return trip

    async def list_for_user(
        self,
        user_id: UUID,
        params: PageParams,
    ) -> tuple[list[Trip], int]:
        return await self.repo.list_by_user(user_id, params)

    async def soft_delete_for_user(
        self,
        trip_id: UUID,
        user_id: UUID,
        session_id: str | None = None,
    ) -> None:
        """Auth-only delete: ownership check then soft-delete + commit."""
        trip = await self.repo.get_with_places(trip_id)
        if trip is None:
            raise TripNotFoundError(trip_id=str(trip_id))
        self.assert_can_access(trip, user_id=user_id, session_id=session_id)
        await self.repo.soft_delete(trip_id)
        await self.session.commit()

    async def claim_trip(
        self,
        trip_id: UUID,
        user_id: UUID,
        session_id: str,
    ) -> Trip:
        """Load trip (404 if missing) then claim_for_user."""
        trip = await self.repo.get_with_places(trip_id)
        if trip is None:
            raise TripNotFoundError(trip_id=str(trip_id))
        return await self.claim_for_user(trip, user_id, session_id)

    def build_geojson(self, trip: Trip) -> dict[str, Any]:
        """
        Build a GeoJSON FeatureCollection from an already-loaded trip.
        Points always; LineStrings when polylines decode. Never raises for None polylines.
        No network I/O.
        """
        features: list[dict[str, Any]] = []
        day_legs: dict[int, list[list[tuple[float, float]]]] = defaultdict(list)

        places = list(getattr(trip, "places", None) or [])
        places.sort(key=lambda tp: (tp.day_number, tp.order_in_day))

        for tp in places:
            name: str | None = None
            lat: float | None = None
            lng: float | None = None
            place = getattr(tp, "place", None)
            if place is not None:
                name = place.name
                point = to_shape(place.location)
                lat = float(point.y)
                lng = float(point.x)

            if lat is not None and lng is not None:
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lng, lat],
                        },
                        "properties": {
                            "name": name,
                            "day": tp.day_number,
                            "order": tp.order_in_day,
                            "suggested_start_time": tp.suggested_start_time,
                            "place_id": str(tp.place_id),
                            "trip_place_id": str(tp.id),
                        },
                    }
                )

            decoded = decode_polyline(tp.polyline)
            if decoded:
                day_legs[tp.day_number].append(decoded)

        for day_number, legs in sorted(day_legs.items()):
            coords = _concat_day_coords(legs)
            if len(coords) < 2:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords,
                    },
                    "properties": {
                        "day": day_number,
                        "trip_id": str(trip.id),
                    },
                }
            )

        return {"type": "FeatureCollection", "features": features}
