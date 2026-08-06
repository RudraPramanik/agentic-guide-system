"""Trip service — save_from_state UoW, ownership, claim, GeoJSON, day surgery.

P7 edit concurrency: last-write-wins — no row locking in MVP.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.pagination import PageParams
from src.destinations.repository import DestinationRepository
from src.evaluation.service import EvaluationService
from src.places.repository import PlaceRepository
from src.planner.routing_provider import OsrmRoutingProvider
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.protocols import RouteLeg, RoutingProvider, legs_to_lookup
from src.travel_engine.route_optimizer import (
    OptimizeResult,
    optimize_route,
    populate_leg_polylines,
)
from src.travel_engine.schedule_builder import ScheduledStop, build_day_schedule
from src.travel_engine.travel_rules import BASE_SENTINEL_ID
from src.travel_engine.trip_validator import (
    DayPlan,
    TripItinerary,
    validate_trip,
)
from src.trips.exceptions import (
    TripAlreadyClaimedError,
    TripEditValidationError,
    TripForbiddenError,
    TripNotFoundError,
    TripStopConflictError,
    TripStopNotFoundError,
)
from src.trips.models import EditType, Trip, TripPlace, TripStatus
from src.trips.polyline import decode_polyline
from src.trips.repository import TripRepository

_MORNING_SLOT_PREFIX = "morning_slot_violation"

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


def _coerce_base_float(value: Any) -> float | None:
    """Return float if value coerces; None if missing or not coercible."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _preferences_from_state(state: dict[str, Any]) -> dict[str, Any]:
    preferences: dict[str, Any] = {
        "interests": state.get("interests") or [],
        "budget": state.get("budget"),
        "include_offbeat": state.get("include_offbeat"),
        "include_trekking": state.get("include_trekking"),
    }
    base_lat = _coerce_base_float(state.get("base_lat"))
    base_lng = _coerce_base_float(state.get("base_lng"))
    if base_lat is not None and base_lng is not None:
        preferences["base_lat"] = base_lat
        preferences["base_lng"] = base_lng
    return preferences


def _resolve_base(trip: Trip, destination: Any) -> tuple[float, float]:
    """
    Prefer trip.preferences base_lat/base_lng when both are numeric (non-bool).
    Else destination.lat / destination.lng.

    Trips saved before P7.0 omit base prefs — destination centroid is the
    known MVP fallback for edit-time routing.
    """
    prefs = trip.preferences or {}
    lat, lng = prefs.get("base_lat"), prefs.get("base_lng")
    if (
        isinstance(lat, (int, float))
        and not isinstance(lat, bool)
        and isinstance(lng, (int, float))
        and not isinstance(lng, bool)
    ):
        return float(lat), float(lng)
    return float(destination.lat), float(destination.lng)


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


def _hydrate_scored(trip_place: TripPlace) -> ScoredPlace:
    """Build ScoredPlace from joined Place (score=1.0 for edit-time hydrate)."""
    place = trip_place.place
    if place is None:
        raise TripEditValidationError(
            "trip place missing joined Place for hydration",
            details={"trip_place_id": str(trip_place.id)},
        )
    point = to_shape(place.location)
    tags = place.enriched_tags if isinstance(place.enriched_tags, list) else []
    return ScoredPlace(
        place=PlaceCandidate(
            id=place.id,
            name=place.name,
            category=place.category,
            enriched_tags=[str(t) for t in tags],
            lat=float(point.y),
            lng=float(point.x),
        ),
        score=1.0,
        score_breakdown={},
    )


def _snapshot_day(places_for_day: list[TripPlace]) -> list[dict[str, Any]]:
    return [
        {
            "place_id": str(tp.place_id),
            "order_in_day": tp.order_in_day,
            "travel_time_min": tp.travel_time_min,
            "visit_duration_min": tp.visit_duration_min,
            "suggested_start_time": tp.suggested_start_time,
            "polyline": tp.polyline,
        }
        for tp in sorted(places_for_day, key=lambda p: p.order_in_day)
    ]


def _consecutive_legs_for_order(
    order: list[ScoredPlace],
    lookup: dict[tuple[UUID, UUID], RouteLeg],
) -> list[RouteLeg]:
    if not order:
        return []
    legs: list[RouteLeg] = []
    first_key = (BASE_SENTINEL_ID, order[0].place.id)
    first = lookup.get(first_key)
    if first is None:
        raise TripEditValidationError(
            f"missing route leg for base -> {order[0].place.id}",
        )
    legs.append(first)
    for i in range(len(order) - 1):
        key = (order[i].place.id, order[i + 1].place.id)
        hop = lookup.get(key)
        if hop is None:
            raise TripEditValidationError(
                f"missing route leg for {order[i].place.id} -> {order[i + 1].place.id}",
            )
        legs.append(hop)
    return legs


def _polyline_by_place_id(
    ordered: list[ScoredPlace],
    leg_polylines: list[str | None],
) -> dict[UUID, str | None]:
    out: dict[UUID, str | None] = {}
    for i, scored in enumerate(ordered):
        out[scored.place.id] = leg_polylines[i] if i < len(leg_polylines) else None
    return out


def _travel_into_stop(
    lookup: dict[tuple[UUID, UUID], RouteLeg],
    frm: UUID,
    to: UUID,
) -> int:
    leg = lookup.get((frm, to))
    return int(leg.duration_min) if leg is not None else 0


def _day_plan_from_scheduled(
    scheduled: list[ScheduledStop],
    legs: list[RouteLeg],
) -> DayPlan:
    lookup = legs_to_lookup(legs)
    total = 0
    prev = BASE_SENTINEL_ID
    for stop in scheduled:
        total += _travel_into_stop(lookup, prev, stop.place.id)
        prev = stop.place.id
    return DayPlan(stops=scheduled, total_travel_min=total)


def _day_plan_from_stored(places_for_day: list[TripPlace]) -> DayPlan:
    ordered = sorted(places_for_day, key=lambda p: p.order_in_day)
    stops = [
        ScheduledStop(
            place=_hydrate_scored(tp).place,
            score=1.0,
            visit_duration_min=tp.visit_duration_min,
            suggested_start_time=tp.suggested_start_time or "08:00",
            arrival_note=tp.arrival_note,
        )
        for tp in ordered
    ]
    total = sum(int(tp.travel_time_min or 0) for tp in ordered)
    return DayPlan(stops=stops, total_travel_min=total)


def _reject_if_dropped(result: OptimizeResult) -> None:
    if not result.dropped_stops:
        return
    details = {
        "dropped_stops": [
            {
                "place_id": str(d.place_id),
                "name": d.name,
                "reason": d.reason,
            }
            for d in result.dropped_stops
        ]
    }
    raise TripEditValidationError(
        "edit would drop other stops",
        code="edit_would_drop_other_stops",
        details=details,
    )


class TripService:
    """
    Trip persistence + P7 day surgery.

    Concurrent edits are last-write-wins (no SELECT FOR UPDATE in P7).
    """

    def __init__(
        self,
        session: AsyncSession,
        routing: RoutingProvider | None = None,
    ) -> None:
        self.session = session
        self.repo = TripRepository(session)
        self._routing = routing if routing is not None else OsrmRoutingProvider()
        self._dest_repo = DestinationRepository(session)
        self._place_repo = PlaceRepository(session)

    def _routing_or(self, routing: RoutingProvider | None) -> RoutingProvider:
        return routing if routing is not None else self._routing

    @staticmethod
    def _resolve_base(trip: Trip, destination: Any) -> tuple[float, float]:
        """Delegate to module helper — prefs base wins, else destination centroid."""
        return _resolve_base(trip, destination)

    def _places_for_day(self, trip: Trip, day: int) -> list[TripPlace]:
        return [
            tp
            for tp in (getattr(trip, "places", None) or [])
            if tp.day_number == day
        ]

    async def _load_owned_trip(self, trip_id: UUID, user_id: UUID) -> Trip:
        trip = await self.repo.get_with_places(trip_id)
        if trip is None:
            raise TripNotFoundError(trip_id=str(trip_id))
        if trip.user_id != user_id:
            raise TripForbiddenError()
        return trip

    async def _fixed_order_day(
        self,
        scored_in_order: list[ScoredPlace],
        base_lat: float,
        base_lng: float,
        routing: RoutingProvider,
    ) -> tuple[list[ScoredPlace], list[RouteLeg], list[str | None]]:
        """Matrix once + consecutive legs + polylines. Must not call optimize_route."""
        if not scored_in_order:
            return [], [], []
        waypoints: list[tuple[UUID, float, float]] = [
            (BASE_SENTINEL_ID, base_lat, base_lng),
            *[(s.place.id, s.place.lat, s.place.lng) for s in scored_in_order],
        ]
        matrix = await routing.travel_matrix(waypoints)
        lookup = legs_to_lookup(matrix)
        consecutive = _consecutive_legs_for_order(scored_in_order, lookup)
        leg_polylines, _day_poly = await populate_leg_polylines(
            scored_in_order, base_lat, base_lng, routing
        )
        return scored_in_order, consecutive, leg_polylines

    async def _optimize_day(
        self,
        day_places: list[ScoredPlace],
        base_lat: float,
        base_lng: float,
        routing: RoutingProvider,
    ) -> OptimizeResult:
        return await optimize_route(day_places, base_lat, base_lng, routing)

    def _schedule_mutated_day(
        self,
        ordered: list[ScoredPlace],
        legs: list[RouteLeg],
        *,
        preserve_order: bool,
    ) -> list[ScheduledStop]:
        return build_day_schedule(ordered, legs, preserve_order=preserve_order)

    def _validate_full_trip(
        self,
        trip: Trip,
        mutated_day_number: int,
        new_day_plan: DayPlan,
        *,
        edit_type: EditType,
    ) -> None:
        days_present = sorted(
            {tp.day_number for tp in (trip.places or [])} | {mutated_day_number}
        )
        day_plans: list[DayPlan] = []
        for day_num in days_present:
            if day_num == mutated_day_number:
                day_plans.append(new_day_plan)
            else:
                stored = self._places_for_day(trip, day_num)
                if not stored:
                    continue
                day_plans.append(_day_plan_from_stored(stored))

        result = validate_trip(TripItinerary(days=day_plans))
        errors = list(result.errors)
        warnings = list(result.warnings)

        if edit_type == EditType.REORDER:
            kept: list[str] = []
            for err in errors:
                if err.startswith(_MORNING_SLOT_PREFIX):
                    warnings.append(err)
                else:
                    kept.append(err)
            errors = kept

        if errors:
            raise TripEditValidationError(
                "trip edit failed validation",
                details={"errors": errors, "warnings": warnings},
            )

    async def _persist_day_and_audit(
        self,
        trip: Trip,
        day: int,
        *,
        scheduled: list[ScheduledStop],
        legs: list[RouteLeg],
        ordered_for_poly: list[ScoredPlace],
        leg_polylines: list[str | None],
        before: list[dict[str, Any]],
        edit_type: EditType,
        place_id: UUID | None = None,
    ) -> Trip:
        lookup = legs_to_lookup(legs)
        poly_map = _polyline_by_place_id(ordered_for_poly, leg_polylines)
        after: list[dict[str, Any]] = []
        existing_by_place = {
            tp.place_id: tp for tp in self._places_for_day(trip, day)
        }
        scheduled_ids = {stop.place.id for stop in scheduled}

        try:
            # SQL DELETE — not session.delete(): Trip.places has cascade
            # delete-orphan, which resurrects ORM-deleted children still in the
            # parent's collection on flush.
            for pid, tp in list(existing_by_place.items()):
                if pid not in scheduled_ids:
                    await self.repo.delete_trip_place(trip.id, pid, day)
                    del existing_by_place[pid]

            new_rows: list[dict[str, Any]] = []
            prev = BASE_SENTINEL_ID
            for i, stop in enumerate(scheduled):
                travel = _travel_into_stop(lookup, prev, stop.place.id)
                poly = poly_map.get(stop.place.id)
                order_in_day = i + 1
                existing = existing_by_place.get(stop.place.id)
                if existing is not None:
                    existing.order_in_day = order_in_day
                    existing.travel_time_min = travel
                    existing.visit_duration_min = stop.visit_duration_min
                    existing.suggested_start_time = stop.suggested_start_time
                    existing.arrival_note = stop.arrival_note
                    existing.polyline = poly
                else:
                    new_rows.append(
                        {
                            "trip_id": trip.id,
                            "place_id": stop.place.id,
                            "day_number": day,
                            "order_in_day": order_in_day,
                            "travel_time_min": travel,
                            "visit_duration_min": stop.visit_duration_min,
                            "suggested_start_time": stop.suggested_start_time,
                            "arrival_note": stop.arrival_note,
                            "polyline": poly,
                        }
                    )
                after.append(
                    {
                        "place_id": str(stop.place.id),
                        "order_in_day": order_in_day,
                        "travel_time_min": travel,
                        "visit_duration_min": stop.visit_duration_min,
                        "suggested_start_time": stop.suggested_start_time,
                        "polyline": poly,
                    }
                )
                prev = stop.place.id

            if new_rows:
                await self.repo.create_trip_places(new_rows)
            await self.session.flush()
            await self.repo.insert_edit_event(
                trip_id=trip.id,
                edit_type=edit_type,
                day_number=day,
                place_id=place_id,
                payload={"before": before, "after": after},
            )
            await EvaluationService(self.session).mark_trip_edited(trip.id)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # Drop stale identity-map collections (expire_on_commit=False in tests)
        self.session.expire(trip, ["places"])
        loaded = await self.repo.get_with_places(trip.id)
        assert loaded is not None
        return loaded

    async def reorder_stops(
        self,
        trip_id: UUID,
        day: int,
        place_ids: list[UUID],
        user_id: UUID,
        *,
        routing: RoutingProvider | None = None,
    ) -> Trip:
        trip = await self._load_owned_trip(trip_id, user_id)
        dest = await self._dest_repo.get_by_id(trip.destination_id)
        if dest is None:
            raise NotFoundError(
                message="Destination not found",
                details={"id": str(trip.destination_id)},
            )
        base_lat, base_lng = self._resolve_base(trip, dest)
        day_stops = self._places_for_day(trip, day)
        before = _snapshot_day(day_stops)
        current_ids = [tp.place_id for tp in day_stops]
        if len(place_ids) != len(current_ids) or set(place_ids) != set(current_ids):
            raise TripEditValidationError(
                "reorder place_ids must be an exact permutation of the day's stops",
                details={
                    "expected": [str(i) for i in current_ids],
                    "got": [str(i) for i in place_ids],
                },
            )

        by_id = {tp.place_id: tp for tp in day_stops}
        scored = [_hydrate_scored(by_id[pid]) for pid in place_ids]
        provider = self._routing_or(routing)
        ordered, consecutive, leg_polylines = await self._fixed_order_day(
            scored, base_lat, base_lng, provider
        )
        scheduled = self._schedule_mutated_day(
            ordered, consecutive, preserve_order=True
        )
        self._validate_full_trip(
            trip,
            day,
            _day_plan_from_scheduled(scheduled, consecutive),
            edit_type=EditType.REORDER,
        )
        return await self._persist_day_and_audit(
            trip,
            day,
            scheduled=scheduled,
            legs=consecutive,
            ordered_for_poly=ordered,
            leg_polylines=leg_polylines,
            before=before,
            edit_type=EditType.REORDER,
        )

    async def remove_stop(
        self,
        trip_id: UUID,
        day: int,
        place_id: UUID,
        user_id: UUID,
        *,
        routing: RoutingProvider | None = None,
    ) -> Trip:
        trip = await self._load_owned_trip(trip_id, user_id)
        dest = await self._dest_repo.get_by_id(trip.destination_id)
        if dest is None:
            raise NotFoundError(
                message="Destination not found",
                details={"id": str(trip.destination_id)},
            )
        base_lat, base_lng = self._resolve_base(trip, dest)
        day_stops = self._places_for_day(trip, day)
        before = _snapshot_day(day_stops)
        if not any(tp.place_id == place_id for tp in day_stops):
            raise TripStopNotFoundError()
        if len(day_stops) == 1:
            raise TripEditValidationError(
                "day would be empty after remove",
                code="day_would_be_empty",
            )

        remaining = [
            _hydrate_scored(tp) for tp in day_stops if tp.place_id != place_id
        ]
        provider = self._routing_or(routing)
        result = await self._optimize_day(remaining, base_lat, base_lng, provider)
        _reject_if_dropped(result)
        scheduled = self._schedule_mutated_day(
            result.ordered, result.legs, preserve_order=False
        )
        self._validate_full_trip(
            trip,
            day,
            _day_plan_from_scheduled(scheduled, result.legs),
            edit_type=EditType.REMOVE_STOP,
        )
        return await self._persist_day_and_audit(
            trip,
            day,
            scheduled=scheduled,
            legs=result.legs,
            ordered_for_poly=result.ordered,
            leg_polylines=result.leg_polylines,
            before=before,
            edit_type=EditType.REMOVE_STOP,
            place_id=place_id,
        )

    async def add_stop(
        self,
        trip_id: UUID,
        day: int,
        place_id: UUID,
        user_id: UUID,
        *,
        routing: RoutingProvider | None = None,
    ) -> Trip:
        trip = await self._load_owned_trip(trip_id, user_id)
        dest = await self._dest_repo.get_by_id(trip.destination_id)
        if dest is None:
            raise NotFoundError(
                message="Destination not found",
                details={"id": str(trip.destination_id)},
            )
        base_lat, base_lng = self._resolve_base(trip, dest)
        day_stops = self._places_for_day(trip, day)
        before = _snapshot_day(day_stops)

        place = await self._place_repo.get_by_id(place_id)
        if place is None:
            raise NotFoundError(
                message="Place not found",
                details={"id": str(place_id)},
            )
        if place.destination_id != trip.destination_id:
            raise TripEditValidationError(
                "place belongs to a different destination",
                details={
                    "place_destination_id": str(place.destination_id),
                    "trip_destination_id": str(trip.destination_id),
                },
            )
        if any(tp.place_id == place_id for tp in (trip.places or [])):
            raise TripStopConflictError()

        point = to_shape(place.location)
        tags = place.enriched_tags if isinstance(place.enriched_tags, list) else []
        new_scored = ScoredPlace(
            place=PlaceCandidate(
                id=place.id,
                name=place.name,
                category=place.category,
                enriched_tags=[str(t) for t in tags],
                lat=float(point.y),
                lng=float(point.x),
            ),
            score=1.0,
            score_breakdown={},
        )
        candidates = [_hydrate_scored(tp) for tp in day_stops] + [new_scored]
        provider = self._routing_or(routing)
        result = await self._optimize_day(candidates, base_lat, base_lng, provider)
        _reject_if_dropped(result)
        scheduled = self._schedule_mutated_day(
            result.ordered, result.legs, preserve_order=False
        )
        self._validate_full_trip(
            trip,
            day,
            _day_plan_from_scheduled(scheduled, result.legs),
            edit_type=EditType.ADD_STOP,
        )
        return await self._persist_day_and_audit(
            trip,
            day,
            scheduled=scheduled,
            legs=result.legs,
            ordered_for_poly=result.ordered,
            leg_polylines=result.leg_polylines,
            before=before,
            edit_type=EditType.ADD_STOP,
            place_id=place_id,
        )

    async def reoptimize_day(
        self,
        trip_id: UUID,
        day: int,
        user_id: UUID,
        *,
        routing: RoutingProvider | None = None,
    ) -> Trip:
        trip = await self._load_owned_trip(trip_id, user_id)
        dest = await self._dest_repo.get_by_id(trip.destination_id)
        if dest is None:
            raise NotFoundError(
                message="Destination not found",
                details={"id": str(trip.destination_id)},
            )
        base_lat, base_lng = self._resolve_base(trip, dest)
        day_stops = self._places_for_day(trip, day)
        before = _snapshot_day(day_stops)
        if not day_stops:
            raise TripEditValidationError(
                "day has no stops to reoptimize",
                details={"day": day},
            )

        scored = [_hydrate_scored(tp) for tp in day_stops]
        provider = self._routing_or(routing)
        result = await self._optimize_day(scored, base_lat, base_lng, provider)
        _reject_if_dropped(result)
        scheduled = self._schedule_mutated_day(
            result.ordered, result.legs, preserve_order=False
        )
        self._validate_full_trip(
            trip,
            day,
            _day_plan_from_scheduled(scheduled, result.legs),
            edit_type=EditType.REOPTIMIZE_DAY,
        )
        return await self._persist_day_and_audit(
            trip,
            day,
            scheduled=scheduled,
            legs=result.legs,
            ordered_for_poly=result.ordered,
            leg_polylines=result.leg_polylines,
            before=before,
            edit_type=EditType.REOPTIMIZE_DAY,
        )

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
        preferences = _preferences_from_state(state)
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
