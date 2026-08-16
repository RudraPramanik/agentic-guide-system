"""Tests for planner OsrmRoutingProvider (mocked get_route — no network)."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.geo.schemas import RouteResult
from src.planner.routing_provider import (
    HaversineRoutingProvider,
    OsrmRoutingProvider,
    get_routing_provider,
)


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


@pytest.mark.asyncio
async def test_haversine_matrix_three_waypoints_no_get_route():
    provider = HaversineRoutingProvider()
    a, b, c = uuid4(), uuid4(), uuid4()
    waypoints = [
        (a, 27.04, 88.26),
        (b, 27.03, 88.27),
        (c, 27.05, 88.25),
    ]
    with patch(
        "src.planner.routing_provider.get_route",
        new_callable=AsyncMock,
    ) as mock_route:
        legs = await provider.travel_matrix(waypoints)
    assert mock_route.await_count == 0
    assert len(legs) == 6
    assert all(leg.used_fallback is True for leg in legs)
    assert all(leg.distance_km > 0 for leg in legs)


@pytest.mark.asyncio
async def test_haversine_polyline_always_none():
    provider = HaversineRoutingProvider()
    assert await provider.route_polyline([(27.04, 88.26), (27.03, 88.27)]) is None


@pytest.mark.asyncio
async def test_haversine_single_waypoint_empty():
    provider = HaversineRoutingProvider()
    assert await provider.travel_matrix([(uuid4(), 27.0, 88.0)]) == []


def test_factory_default_and_unknown_are_haversine():
    fake = SimpleNamespace(ROUTING_BACKEND="haversine")
    with patch("src.planner.routing_provider.get_settings", return_value=fake):
        assert isinstance(get_routing_provider(), HaversineRoutingProvider)
    fake.ROUTING_BACKEND = "not-a-backend"
    with patch("src.planner.routing_provider.get_settings", return_value=fake):
        assert isinstance(get_routing_provider(), HaversineRoutingProvider)


def test_factory_osrm_returns_osrm_adapter():
    fake = SimpleNamespace(ROUTING_BACKEND="osrm")
    with patch("src.planner.routing_provider.get_settings", return_value=fake):
        assert isinstance(get_routing_provider(), OsrmRoutingProvider)


@pytest.mark.asyncio
async def test_generate_default_routing_uses_factory():
    from src.planner.service import PlannerService

    dest_id = uuid4()
    sentinel = object()
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "destination_id": str(dest_id),
            "plan_complete": False,
            "needs_clarification": False,
            "abort_triggered": True,
            "schedule": [],
            "itinerary": {},
            "errors": ["test_short_circuit"],
            "warnings": [],
        }
    )
    with (
        patch("src.planner.service.get_compiled_graph", return_value=mock_graph),
        patch(
            "src.planner.service.record_evaluation",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "src.planner.service.get_routing_provider",
            return_value=sentinel,
        ) as factory,
    ):
        await PlannerService().generate(
            destination_id=dest_id,
            raw_input="trip",
            base_lat=27.0,
            base_lng=88.0,
            session_id="sess-test",
        )
    factory.assert_called_once()
    _args, kwargs = mock_graph.ainvoke.call_args
    ctx = kwargs["config"]["configurable"]["tool_context"]
    assert ctx.routing is sentinel


def test_trip_service_default_routing_uses_factory():
    from src.trips.service import TripService

    sentinel = object()
    session = MagicMock()
    with patch("src.trips.service.get_routing_provider", return_value=sentinel):
        svc = TripService(session)
    assert svc._routing is sentinel


def test_travel_engine_has_zero_geo_imports():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src" / "travel_engine"
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "src.geo" not in text
        assert "from src import geo" not in text

