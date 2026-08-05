"""Trip service — save_from_state UoW, ownership, and claim. No FastAPI / PlannerService."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.trips.exceptions import TripAlreadyClaimedError, TripForbiddenError
from src.trips.models import Trip, TripStatus
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
        await self.session.refresh(trip)
        return trip
