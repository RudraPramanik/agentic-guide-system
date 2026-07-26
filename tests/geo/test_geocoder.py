"""Geocoder gateway unit tests — mocked Nominatim, no network."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from src.geo import geocoder


@pytest.fixture(autouse=True)
def _clear_geocode_cache() -> None:
    geocoder._clear_cache_for_tests()
    yield
    geocoder._clear_cache_for_tests()


@pytest.mark.asyncio
async def test_geocode_success(mocker) -> None:
    mocker.patch.object(
        geocoder,
        "_fetch_nominatim",
        new=AsyncMock(
            return_value=[
                {
                    "lat": "27.041",
                    "lon": "88.263",
                    "osm_type": "relation",
                    "osm_id": 123,
                    "name": "Darjeeling",
                    "display_name": "Darjeeling, West Bengal, India",
                    "address": {"country_code": "in"},
                }
            ]
        ),
    )

    result = await geocoder.geocode("Darjeeling")

    assert result is not None
    assert result.name == "Darjeeling"
    assert abs(result.lat - 27.041) < 0.001
    assert abs(result.lng - 88.263) < 0.001
    assert result.osm_place_id == "relation/123"
    assert result.country == "IN"


@pytest.mark.asyncio
async def test_geocode_failure_returns_none(mocker) -> None:
    mock_fetch = AsyncMock(side_effect=httpx.ConnectError("down"))
    mocker.patch.object(geocoder, "_fetch_nominatim", new=mock_fetch)

    result = await geocoder.geocode("Anywhere")

    assert result is None
    assert 1 <= mock_fetch.await_count <= 3


@pytest.mark.asyncio
async def test_geocode_cache_hit_on_repeated_call(mocker) -> None:
    mock_fetch = AsyncMock(
        return_value=[
            {
                "lat": "27.041",
                "lon": "88.263",
                "osm_type": "relation",
                "osm_id": 1,
                "name": "Darjeeling",
                "display_name": "Darjeeling",
                "address": {"country_code": "in"},
            }
        ]
    )
    mocker.patch.object(geocoder, "_fetch_nominatim", new=mock_fetch)

    first = await geocoder.geocode("Darjeeling")
    second = await geocoder.geocode("  DARJEELING  ")

    assert first is not None and second is not None
    assert first.lat == second.lat
    assert mock_fetch.await_count == 1
    assert geocoder.cache_stats()["hits"] >= 1


@pytest.mark.asyncio
async def test_geocode_caches_none_result_too(mocker) -> None:
    mock_fetch = AsyncMock(return_value=[])
    mocker.patch.object(geocoder, "_fetch_nominatim", new=mock_fetch)

    first = await geocoder.geocode("XyzzyNowhere")
    second = await geocoder.geocode("xyzzynowhere")

    assert first is None and second is None
    assert mock_fetch.await_count == 1
