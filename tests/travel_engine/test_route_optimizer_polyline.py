"""P6.0 / P7.1 — polyline threading through optimize_route + shared helper."""

from __future__ import annotations

import pytest

from tests.travel_engine.fake_routing import FakeRoutingProvider
from tests.travel_engine.test_route_optimizer import _scored
from src.travel_engine.route_optimizer import optimize_route, populate_leg_polylines


@pytest.mark.asyncio
async def test_leg_polylines_aligned_and_day_polyline() -> None:
    places = [_scored(n) for n in ("A", "B", "C")]
    fake = FakeRoutingProvider()
    result = await optimize_route(places, 0.0, 0.0, fake)
    assert len(result.legs) == 12  # full pairwise BASE+3, not consecutive-only
    assert len(result.leg_polylines) == len(result.ordered) == 3
    assert all(p is not None for p in result.leg_polylines)
    assert result.day_polyline == "poly_4pts"
    assert fake.polyline_call_count == 4  # N legs + 1 day


@pytest.mark.asyncio
async def test_polyline_none_on_fallback_no_raise() -> None:
    places = [_scored(n) for n in ("A", "B", "C")]
    fake = FakeRoutingProvider(polyline_for=lambda _w: None)
    result = await optimize_route(places, 0.0, 0.0, fake)
    assert len(result.ordered) == 3
    assert result.leg_polylines == [None, None, None]
    assert result.day_polyline is None


@pytest.mark.asyncio
async def test_populate_leg_polylines_fixed_order_two_stops() -> None:
    ordered = [_scored(n) for n in ("A", "B")]
    fake = FakeRoutingProvider()
    leg_polylines, day_polyline = await populate_leg_polylines(
        ordered, 0.0, 0.0, fake
    )
    assert len(leg_polylines) == 2
    assert all(p is not None for p in leg_polylines)
    assert day_polyline == "poly_3pts"
    assert fake.polyline_call_count == 3  # 2 legs + day


@pytest.mark.asyncio
async def test_populate_leg_polylines_empty_and_soft_fail() -> None:
    fake = FakeRoutingProvider()
    empty_legs, empty_day = await populate_leg_polylines([], 0.0, 0.0, fake)
    assert empty_legs == []
    assert empty_day is None
    assert fake.polyline_call_count == 0

    ordered = [_scored(n) for n in ("A", "B")]
    soft = FakeRoutingProvider(polyline_for=lambda _w: None)
    legs, day = await populate_leg_polylines(ordered, 0.0, 0.0, soft)
    assert legs == [None, None]
    assert day is None
