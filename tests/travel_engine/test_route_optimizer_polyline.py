"""P6.0 / 6.5 regression — polyline threading through optimize_route."""

from __future__ import annotations

import pytest

from tests.travel_engine.fake_routing import FakeRoutingProvider
from tests.travel_engine.test_route_optimizer import _scored
from src.travel_engine.route_optimizer import optimize_route


@pytest.mark.asyncio
async def test_leg_polylines_aligned_and_day_polyline() -> None:
    places = [_scored(n) for n in ("A", "B", "C")]
    fake = FakeRoutingProvider()
    result = await optimize_route(places, 0.0, 0.0, fake)
    assert len(result.leg_polylines) == len(result.ordered) == 3
    assert all(p is not None for p in result.leg_polylines)
    assert result.day_polyline == "poly_4pts"
    assert fake.polyline_call_count == 4  # N legs + 1 day


@pytest.mark.asyncio
async def test_polyline_none_on_fallback_no_raise() -> None:
    places = [_scored(n) for n in ("A", "B", "C")]
    fake = FakeRoutingProvider(polyline_for=lambda _w: None)
    result = await optimize_route(places, 0.0, 0.0, fake)
    assert result.leg_polylines == [None, None, None]
    assert result.day_polyline is None
