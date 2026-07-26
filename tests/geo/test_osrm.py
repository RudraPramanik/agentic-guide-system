"""OSRM gateway unit tests — mocked HTTP, no network."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.geo import osrm


@pytest.mark.asyncio
async def test_get_route_success_converts_units_and_uses_lng_lat_url_order(mocker) -> None:
    mock_call = AsyncMock(
        return_value={
            "routes": [
                {
                    "distance": 1400.0,
                    "duration": 180.0,
                    "geometry": "encodedpoly",
                }
            ]
        }
    )
    mocker.patch.object(osrm, "_call_osrm", new=mock_call)

    result = await osrm.get_route([(27.04, 88.26), (27.03, 88.27)])

    assert result.fallback_used is False
    assert abs(result.distance_km - 1.4) < 1e-9
    assert abs(result.duration_min - 3.0) < 1e-9
    assert result.encoded_polyline == "encodedpoly"
    waypoints = mock_call.await_args.args[0]
    assert waypoints == [(27.04, 88.26), (27.03, 88.27)]


@pytest.mark.asyncio
async def test_get_route_fallback_when_osrm_none(mocker) -> None:
    mocker.patch.object(osrm, "_call_osrm", new=AsyncMock(return_value=None))

    result = await osrm.get_route([(27.04, 88.26), (27.03, 88.27)])

    assert result.fallback_used is True
    assert result.distance_km > 0
    assert result.duration_min > 0
    assert result.encoded_polyline is None


@pytest.mark.asyncio
async def test_get_route_rejects_fewer_than_two_waypoints() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        await osrm.get_route([(27.04, 88.26)])
