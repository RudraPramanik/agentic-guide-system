"""Return-to-base mode on optimize_route. Default stays open-jaw."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.protocols import RouteLeg
from src.travel_engine.route_optimizer import optimize_route
from src.travel_engine.travel_rules import BASE_SENTINEL_ID, MAX_DAILY_TRAVEL_MIN
from tests.travel_engine.fake_routing import FakeRoutingProvider


def _scored(
    name: str,
    *,
    score: float = 1.0,
    place_id: UUID | None = None,
) -> ScoredPlace:
    return ScoredPlace(
        place=PlaceCandidate(
            id=place_id or uuid4(),
            name=name,
            category="attraction",
            enriched_tags=[],
            lat=1.0,
            lng=2.0,
        ),
        score=score,
        score_breakdown={},
    )


class _FallbackReturn(FakeRoutingProvider):
    async def travel_matrix(self, waypoints):
        legs = await super().travel_matrix(waypoints)
        marked: list[RouteLeg] = []
        for leg in legs:
            if (
                leg.to_place_id == BASE_SENTINEL_ID
                and leg.from_place_id != BASE_SENTINEL_ID
            ):
                marked.append(leg.model_copy(update={"used_fallback": True}))
            else:
                marked.append(leg)
        return marked


@pytest.mark.asyncio
async def test_return_mode_off_excludes_return_from_score() -> None:
    places = [_scored("A"), _scored("B")]
    fake = FakeRoutingProvider(default_duration_min=10, default_distance_km=1.0)
    result = await optimize_route(places, 0.0, 0.0, fake, return_to_base=False)
    assert result.total_travel_min == 20
    assert result.return_polyline is None
    assert len(result.leg_polylines) == 2
    assert fake.polyline_call_count == len(result.ordered) + 1
    assert BASE_SENTINEL_ID not in {stop.place.id for stop in result.ordered}


@pytest.mark.asyncio
async def test_return_mode_on_adds_last_stop_to_base() -> None:
    places = [_scored("A"), _scored("B")]
    fake = FakeRoutingProvider(default_duration_min=10, default_distance_km=1.0)
    result = await optimize_route(places, 0.0, 0.0, fake, return_to_base=True)
    assert result.total_travel_min == 30
    assert result.return_polyline == "poly_2pts"
    assert len(result.leg_polylines) == 2
    assert result.day_polyline == "poly_4pts"
    assert fake.polyline_call_count == len(result.ordered) + 2
    assert BASE_SENTINEL_ID not in {stop.place.id for stop in result.ordered}
    assert all(
        set(leg.model_fields) == {
            "from_place_id",
            "to_place_id",
            "duration_min",
            "distance_km",
            "used_fallback",
        }
        for leg in result.legs
    )


@pytest.mark.asyncio
async def test_fallback_return_leg_is_kept() -> None:
    places = [_scored("A")]
    fake = _FallbackReturn(default_duration_min=10, default_distance_km=1.0)
    result = await optimize_route(places, 0.0, 0.0, fake, return_to_base=True)
    returns = [
        leg
        for leg in result.legs
        if leg.to_place_id == BASE_SENTINEL_ID
        and leg.from_place_id == result.ordered[0].place.id
    ]
    assert returns
    assert returns[0].used_fallback is True
    assert result.total_travel_min == 20


@pytest.mark.asyncio
async def test_return_mode_drop_when_round_trip_exceeds_cap() -> None:
    high = _scored("High", score=5.0)
    low = _scored("Low", score=1.0)

    def duration_for(frm: UUID, to: UUID) -> tuple[int, float]:
        if to == BASE_SENTINEL_ID and frm != BASE_SENTINEL_ID:
            return 200, 1.0
        return 40, 1.0

    fake = FakeRoutingProvider(duration_for)
    result = await optimize_route(
        [high, low], 0.0, 0.0, fake, return_to_base=True
    )
    assert result.dropped_stops
    assert all(item.reason == "exceeded_max_daily_travel" for item in result.dropped_stops)
    assert result.total_travel_min > MAX_DAILY_TRAVEL_MIN
    assert result.still_over_budget is True
    open_jaw = await optimize_route(
        [high, low], 0.0, 0.0, FakeRoutingProvider(duration_for), return_to_base=False
    )
    assert open_jaw.total_travel_min == 80
    assert open_jaw.dropped_stops == []
