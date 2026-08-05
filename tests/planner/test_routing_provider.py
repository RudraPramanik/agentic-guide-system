"""Tests for planner OsrmRoutingProvider (mocked get_route — no network)."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from src.geo.schemas import RouteResult
from src.planner.routing_provider import OsrmRoutingProvider


@pytest.mark.asyncio
async def test_pairwise_matrix_three_waypoints():
    provider = OsrmRoutingProvider()
    a, b, c = uuid4(), uuid4(), uuid4()
    waypoints = [
        (a, 27.0, 88.0),
        (b, 27.1, 88.1),
        (c, 27.2, 88.2),
    ]
    mock_result = RouteResult(
        distance_km=1.5,
        duration_min=12.4,
        fallback_used=False,
    )
    with patch(
        "src.planner.routing_provider.get_route",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_route:
        legs = await provider.travel_matrix(waypoints)
    assert len(legs) == 6  # 3 * 2 directed pairs
    assert mock_route.await_count == 6
    assert all(leg.duration_min == 12 for leg in legs)  # round(12.4)
    assert all(leg.used_fallback is False for leg in legs)


@pytest.mark.asyncio
async def test_fallback_flag_maps_to_route_leg():
    provider = OsrmRoutingProvider()
    a, b = uuid4(), uuid4()
    mock_result = RouteResult(
        distance_km=2.0,
        duration_min=20.0,
        fallback_used=True,
    )
    with patch(
        "src.planner.routing_provider.get_route",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        legs = await provider.travel_matrix(
            [(a, 0.0, 0.0), (b, 0.1, 0.1)]
        )
    assert len(legs) == 2
    assert all(leg.used_fallback is True for leg in legs)


@pytest.mark.asyncio
async def test_single_waypoint_empty():
    provider = OsrmRoutingProvider()
    legs = await provider.travel_matrix([(uuid4(), 27.0, 88.0)])
    assert legs == []


@pytest.mark.asyncio
async def test_empty_waypoints():
    provider = OsrmRoutingProvider()
    assert await provider.travel_matrix([]) == []


@pytest.mark.asyncio
async def test_matrix_respects_concurrency_and_beats_serial():
    """Peak in-flight ≤ concurrency; wall time ≪ serial n*(n-1)*delay."""
    n = 4
    delay = 0.05
    concurrency = 3
    pair_count = n * (n - 1)
    serial_floor = pair_count * delay

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()
    mock_result = RouteResult(
        distance_km=1.0,
        duration_min=10.0,
        fallback_used=False,
    )

    async def slow_get_route(_waypoints):
        nonlocal in_flight, peak
        async with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        try:
            await asyncio.sleep(delay)
            return mock_result
        finally:
            async with lock:
                in_flight -= 1

    waypoints = [(uuid4(), 27.0 + i * 0.01, 88.0 + i * 0.01) for i in range(n)]
    provider = OsrmRoutingProvider()
    fake_settings = SimpleNamespace(OSRM_MATRIX_MAX_CONCURRENCY=concurrency)

    with (
        patch("src.planner.routing_provider.get_settings", return_value=fake_settings),
        patch(
            "src.planner.routing_provider.get_route",
            side_effect=slow_get_route,
        ),
    ):
        t0 = time.perf_counter()
        legs = await provider.travel_matrix(waypoints)
        elapsed = time.perf_counter() - t0

    assert len(legs) == pair_count
    assert peak <= concurrency
    # Allow small scheduling overhead; still well under serial cost.
    assert elapsed < serial_floor * 0.7


@pytest.mark.asyncio
async def test_route_polyline_returns_geometry():
    provider = OsrmRoutingProvider()
    mock_result = RouteResult(
        distance_km=1.0,
        duration_min=10.0,
        encoded_polyline="encoded_abc",
        fallback_used=False,
    )
    with patch(
        "src.planner.routing_provider.get_route",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        assert await provider.route_polyline([(0.0, 0.0), (0.1, 0.1)]) == "encoded_abc"


@pytest.mark.asyncio
async def test_route_polyline_fallback_and_errors_are_none():
    provider = OsrmRoutingProvider()
    with patch(
        "src.planner.routing_provider.get_route",
        new_callable=AsyncMock,
        return_value=RouteResult(
            distance_km=1.0, duration_min=10.0, fallback_used=True
        ),
    ):
        assert await provider.route_polyline([(0.0, 0.0), (0.1, 0.1)]) is None

    with patch(
        "src.planner.routing_provider.get_route",
        new_callable=AsyncMock,
        side_effect=ValueError("need 2"),
    ):
        assert await provider.route_polyline([(0.0, 0.0)]) is None
