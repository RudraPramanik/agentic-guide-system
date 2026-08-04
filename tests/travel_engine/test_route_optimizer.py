"""Tests for travel_engine.route_optimizer."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.route_optimizer import optimize_route
from src.travel_engine.travel_rules import (
    BASE_SENTINEL_ID,
    MAX_DAILY_TRAVEL_MIN,
    MAX_PLACES_PER_DAY,
    MAX_ROUTE_DROP_ATTEMPTS,
)
from tests.travel_engine.fake_routing import FakeRoutingProvider


def _scored(
    name: str,
    *,
    score: float = 1.0,
    place_id: UUID | None = None,
    category: str = "attraction",
) -> ScoredPlace:
    return ScoredPlace(
        place=PlaceCandidate(
            id=place_id or uuid4(),
            name=name,
            category=category,
            enriched_tags=[],
            lat=0.0,
            lng=0.0,
        ),
        score=score,
        score_breakdown={},
    )


@pytest.mark.asyncio
async def test_empty_day_short_circuits():
    result = await optimize_route([], 0.0, 0.0, FakeRoutingProvider())
    assert result.ordered == []
    assert result.legs == []
    assert result.total_travel_min == 0
    assert result.dropped_stops == []
    assert result.still_over_budget is False


@pytest.mark.asyncio
async def test_fake_matrix_complete_ordered_day():
    places = [_scored(n) for n in ("A", "B", "C")]
    fake = FakeRoutingProvider()
    result = await optimize_route(places, 0.0, 0.0, fake)
    assert len(result.ordered) == 3
    # Full directed pairwise among BASE + 3 stops (4×3), not consecutive-only —
    # schedule morning-extract needs arbitrary hops.
    assert len(result.legs) == 12
    assert any(
        leg.from_place_id == BASE_SENTINEL_ID
        and leg.to_place_id == result.ordered[0].place.id
        for leg in result.legs
    )
    assert fake.call_count == 1
    assert result.dropped_stops == []
    assert result.still_over_budget is False


@pytest.mark.asyncio
async def test_asymmetric_fake_forces_known_best_order():
    id_a, id_b, id_c = uuid4(), uuid4(), uuid4()
    places = [
        _scored("A", place_id=id_a, score=3.0),
        _scored("B", place_id=id_b, score=2.0),
        _scored("C", place_id=id_c, score=1.0),
    ]

    cheap = {
        (BASE_SENTINEL_ID, id_a): 1,
        (id_a, id_b): 1,
        (id_b, id_c): 1,
    }

    def duration_for(frm: UUID, to: UUID) -> tuple[int, float]:
        return cheap.get((frm, to), 100), 1.0

    result = await optimize_route(places, 0.0, 0.0, FakeRoutingProvider(duration_for))
    assert [s.place.name for s in result.ordered] == ["A", "B", "C"]
    assert result.total_travel_min == 3


@pytest.mark.asyncio
async def test_over_budget_records_dropped_stops():
    places = [
        _scored("High", score=5.0),
        _scored("Mid", score=3.0),
        _scored("Low", score=1.0),
        _scored("Lower", score=0.5),
    ]
    # Every hop huge → always over MAX_DAILY_TRAVEL_MIN (strict >)
    fake = FakeRoutingProvider(default_duration_min=MAX_DAILY_TRAVEL_MIN + 1)
    result = await optimize_route(places, 0.0, 0.0, fake)

    # Thin to one stop (3 drops from 4); still over because single hop is huge
    assert len(result.dropped_stops) == 3
    assert all(d.reason == "exceeded_max_daily_travel" for d in result.dropped_stops)
    assert {d.name for d in result.dropped_stops} == {"Lower", "Low", "Mid"}
    assert len(result.ordered) == 1
    assert result.ordered[0].place.name == "High"
    assert result.still_over_budget is True
    # matrix once per attempt: initial + 3 drops = 4
    assert fake.call_count == 4


@pytest.mark.asyncio
async def test_drop_until_under_budget():
    # 100 min hops: 3 stops → ~300 over; 1 stop → 100 under
    places = [_scored(f"P{i}", score=float(10 - i)) for i in range(3)]
    fake = FakeRoutingProvider(default_duration_min=100)
    result = await optimize_route(places, 0.0, 0.0, fake)
    assert result.still_over_budget is False
    assert result.total_travel_min <= MAX_DAILY_TRAVEL_MIN
    assert len(result.ordered) == 1
    assert len(result.dropped_stops) == 2


@pytest.mark.asyncio
async def test_drop_attempts_allow_full_day_to_one_stop():
    assert MAX_ROUTE_DROP_ATTEMPTS == MAX_PLACES_PER_DAY - 1
    places = [_scored(f"P{i}", score=float(10 - i)) for i in range(MAX_PLACES_PER_DAY)]
    fake = FakeRoutingProvider(default_duration_min=MAX_DAILY_TRAVEL_MIN + 1)
    result = await optimize_route(places, 0.0, 0.0, fake)
    assert len(result.dropped_stops) == MAX_ROUTE_DROP_ATTEMPTS
    assert result.still_over_budget is True
    assert len(result.ordered) == 1
