"""Route optimization — order a day's stops for minimum travel (pure, no I/O).

Template Method: algorithm is fixed; travel times come only via RoutingProvider DI.
Ordering: brute-force permutations (≤ MAX_PLACES_PER_DAY!); no TSP package.
Drop-retry: when best total > MAX_DAILY_TRAVEL_MIN, drop lowest-scored stop
(reason exceeded_max_daily_travel) up to MAX_ROUTE_DROP_ATTEMPTS times.
"""

from __future__ import annotations

from itertools import permutations
from uuid import UUID

from pydantic import BaseModel, Field

from src.travel_engine.place_selector import ScoredPlace
from src.travel_engine.protocols import RouteLeg, RoutingProvider, legs_to_lookup
from src.travel_engine.travel_rules import (
    BASE_SENTINEL_ID,
    MAX_DAILY_TRAVEL_MIN,
    MAX_ROUTE_DROP_ATTEMPTS,
)

_MISSING_LEG_PENALTY = 10**9


class DroppedStop(BaseModel):
    place_id: UUID
    name: str | None = None
    reason: str


class OptimizeResult(BaseModel):
    ordered: list[ScoredPlace] = Field(default_factory=list)
    legs: list[RouteLeg] = Field(default_factory=list)
    total_travel_min: int = 0
    dropped_stops: list[DroppedStop] = Field(default_factory=list)
    still_over_budget: bool = False


def _leg_duration(
    lookup: dict[tuple[UUID, UUID], RouteLeg], from_id: UUID, to_id: UUID
) -> int:
    leg = lookup.get((from_id, to_id))
    if leg is None:
        return _MISSING_LEG_PENALTY
    return leg.duration_min


def _score_order(
    order: tuple[ScoredPlace, ...],
    lookup: dict[tuple[UUID, UUID], RouteLeg],
) -> int:
    if not order:
        return 0
    total = _leg_duration(lookup, BASE_SENTINEL_ID, order[0].place.id)
    for i in range(len(order) - 1):
        total += _leg_duration(lookup, order[i].place.id, order[i + 1].place.id)
    return total


def _consecutive_legs(
    order: list[ScoredPlace],
    lookup: dict[tuple[UUID, UUID], RouteLeg],
) -> list[RouteLeg]:
    if not order:
        return []
    legs: list[RouteLeg] = []
    first_key = (BASE_SENTINEL_ID, order[0].place.id)
    first = lookup.get(first_key)
    if first is None:
        legs.append(
            RouteLeg(
                from_place_id=BASE_SENTINEL_ID,
                to_place_id=order[0].place.id,
                duration_min=_MISSING_LEG_PENALTY,
                distance_km=0.0,
            )
        )
    else:
        legs.append(first)
    for i in range(len(order) - 1):
        key = (order[i].place.id, order[i + 1].place.id)
        hop = lookup.get(key)
        if hop is None:
            legs.append(
                RouteLeg(
                    from_place_id=order[i].place.id,
                    to_place_id=order[i + 1].place.id,
                    duration_min=_MISSING_LEG_PENALTY,
                    distance_km=0.0,
                )
            )
        else:
            legs.append(hop)
    return legs


def _best_order(
    remaining: list[ScoredPlace],
    lookup: dict[tuple[UUID, UUID], RouteLeg],
) -> tuple[list[ScoredPlace], int, list[RouteLeg]]:
    if not remaining:
        return [], 0, []
    best_order: list[ScoredPlace] | None = None
    best_total = _MISSING_LEG_PENALTY * 2
    best_ids: tuple[UUID, ...] | None = None
    for perm in permutations(remaining):
        total = _score_order(perm, lookup)
        ids = tuple(s.place.id for s in perm)
        if best_order is None or total < best_total or (
            total == best_total and (best_ids is None or ids < best_ids)
        ):
            best_order = list(perm)
            best_total = total
            best_ids = ids
    assert best_order is not None
    return best_order, best_total, _consecutive_legs(best_order, lookup)


def _pick_lowest_scored(remaining: list[ScoredPlace]) -> ScoredPlace:
    return min(remaining, key=lambda s: (s.score, s.place.name, str(s.place.id)))


async def optimize_route(
    day_places: list[ScoredPlace],
    base_lat: float,
    base_lng: float,
    routing: RoutingProvider,
) -> OptimizeResult:
    """
    Order day's stops for minimum travel via injected RoutingProvider.

    Calls travel_matrix once per attempt. Drops lowest-scored stops when
    over MAX_DAILY_TRAVEL_MIN (max MAX_ROUTE_DROP_ATTEMPTS).
    """
    if not day_places:
        return OptimizeResult()

    remaining = list(day_places)
    dropped: list[DroppedStop] = []
    drops_done = 0

    while True:
        waypoints: list[tuple[UUID, float, float]] = [
            (BASE_SENTINEL_ID, base_lat, base_lng),
            *[(s.place.id, s.place.lat, s.place.lng) for s in remaining],
        ]
        matrix = await routing.travel_matrix(waypoints)
        lookup = legs_to_lookup(matrix)
        ordered, total, legs = _best_order(remaining, lookup)

        if total <= MAX_DAILY_TRAVEL_MIN or drops_done >= MAX_ROUTE_DROP_ATTEMPTS:
            return OptimizeResult(
                ordered=ordered,
                legs=legs,
                total_travel_min=total if ordered else 0,
                dropped_stops=dropped,
                still_over_budget=bool(ordered) and total > MAX_DAILY_TRAVEL_MIN,
            )

        if len(remaining) <= 1:
            return OptimizeResult(
                ordered=ordered,
                legs=legs,
                total_travel_min=total if ordered else 0,
                dropped_stops=dropped,
                still_over_budget=bool(ordered) and total > MAX_DAILY_TRAVEL_MIN,
            )

        victim = _pick_lowest_scored(remaining)
        remaining = [s for s in remaining if s.place.id != victim.place.id]
        dropped.append(
            DroppedStop(
                place_id=victim.place.id,
                name=victim.place.name,
                reason="exceeded_max_daily_travel",
            )
        )
        drops_done += 1
