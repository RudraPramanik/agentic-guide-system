"""Route optimization — order a day's stops for minimum travel (pure, no I/O).

Template Method: algorithm is fixed; travel times come only via RoutingProvider DI.
Ordering: brute-force permutations (≤ MAX_PLACES_PER_DAY!); no TSP package.
Drop-retry: when best total > MAX_DAILY_TRAVEL_MIN, drop lowest-scored stop
(reason exceeded_max_daily_travel) until under budget or one stop remains
(capped by MAX_ROUTE_DROP_ATTEMPTS).
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
    leg_polylines: list[str | None] = Field(default_factory=list)
    day_polyline: str | None = None


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


async def populate_leg_polylines(
    ordered: list[ScoredPlace],
    base_lat: float,
    base_lng: float,
    routing: RoutingProvider,
) -> tuple[list[str | None], str | None]:
    """
    Geometry for an ALREADY-DECIDED order (no permutation search).

    Returns:
      - leg_polylines: aligned to ordered; index i = polyline INTO ordered[i]
      - day_polyline: aggregate for base + all stops

    Callers: optimize_route (winning order) and P7 reorder fixed-order path.
    At most len(ordered)+1 route_polyline calls; soft-fail None does not raise.
    Does NOT change OptimizeResult.legs — that stays the full pairwise matrix.
    """
    if not ordered:
        return [], None
    waypoints_final: list[tuple[float, float]] = [
        (base_lat, base_lng),
        *[(sp.place.lat, sp.place.lng) for sp in ordered],
    ]
    leg_polylines: list[str | None] = []
    for i in range(len(ordered)):
        leg_polylines.append(
            await routing.route_polyline(waypoints_final[i : i + 2])
        )
    day_polyline = await routing.route_polyline(waypoints_final)
    return leg_polylines, day_polyline


async def optimize_route(
    day_places: list[ScoredPlace],
    base_lat: float,
    base_lng: float,
    routing: RoutingProvider,
) -> OptimizeResult:
    """
    Order day's stops for minimum travel via injected RoutingProvider.

    Calls travel_matrix once per attempt. Drops lowest-scored stops while
    over MAX_DAILY_TRAVEL_MIN and more than one stop remains (capped by
    MAX_ROUTE_DROP_ATTEMPTS).

    ``legs`` is the full pairwise matrix from the final attempt (not only the
    consecutive chain) so schedule morning-only reorder can look up any hop.

    After the winning order is final, populates leg_polylines / day_polyline
    via populate_leg_polylines (not during permutation search or discarded retries).
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
        ordered, total, _consecutive = _best_order(remaining, lookup)
        # Full pairwise matrix so build_day_schedule can re-time after
        # morning-only extract reorder.
        legs = list(matrix)
        under_budget = total <= MAX_DAILY_TRAVEL_MIN

        if under_budget or len(remaining) <= 1:
            leg_polylines, day_polyline = await populate_leg_polylines(
                ordered, base_lat, base_lng, routing
            )
            return OptimizeResult(
                ordered=ordered,
                legs=legs,
                total_travel_min=total if ordered else 0,
                dropped_stops=dropped,
                still_over_budget=bool(ordered) and not under_budget,
                leg_polylines=leg_polylines,
                day_polyline=day_polyline,
            )

        if drops_done >= MAX_ROUTE_DROP_ATTEMPTS:
            leg_polylines, day_polyline = await populate_leg_polylines(
                ordered, base_lat, base_lng, routing
            )
            return OptimizeResult(
                ordered=ordered,
                legs=legs,
                total_travel_min=total if ordered else 0,
                dropped_stops=dropped,
                still_over_budget=True,
                leg_polylines=leg_polylines,
                day_polyline=day_polyline,
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
