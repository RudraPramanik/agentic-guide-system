"""Facade tests — injectable ports, no live Nominatim."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import ExternalServiceError
from src.geo.schemas import GeocodedPlace
from src.location_intelligence.schemas import CatalogHit
from src.location_intelligence.service import LocationIntelligenceService


@pytest.mark.asyncio
async def test_search_does_not_upsert(
    darjeeling: GeocodedPlace,
    darjeeling_catalog: CatalogHit,
) -> None:
    upsert_calls: list[object] = []

    async def geocoder(_q: str) -> list[GeocodedPlace]:
        return [darjeeling]

    async def catalog(_q: str) -> list[CatalogHit]:
        return [darjeeling_catalog]

    # Catalog port never exposes upsert; this list stays empty by construction.
    svc = LocationIntelligenceService(geocoder=geocoder, catalog=catalog)
    result = await svc.search("Darjeeling")
    assert result.status == "resolved"
    assert upsert_calls == []


@pytest.mark.asyncio
async def test_timeout_is_geocoder_timeout(mocker) -> None:
    async def slow(_q: str) -> list[GeocodedPlace]:
        await asyncio.sleep(10)
        return []

    mocker.patch(
        "src.location_intelligence.service.get_settings",
        return_value=type(
            "S",
            (),
            {
                "SEARCH_GEOCODE_TIMEOUT_SECONDS": 0.01,
                "LOCATION_AUTO_RESOLVE_CONFIDENCE": 0.90,
                "LOCATION_POI_RADIUS_KM": 10.0,
                "LOCATION_NEIGHBORHOOD_RADIUS_KM": 5.0,
                "LOCATION_CITY_FALLBACK_RADIUS_KM": 15.0,
                "LOCATION_MAX_RADIUS_KM": 50.0,
            },
        )(),
    )
    svc = LocationIntelligenceService(
        geocoder=slow,
        catalog=AsyncMock(return_value=[]),
    )
    result = await svc.search("Darjeeling")
    assert result.status == "not_found"
    assert result.reason == "geocoder_timeout"


@pytest.mark.asyncio
async def test_policy_rejection_propagates() -> None:
    async def boom(_q: str) -> list[GeocodedPlace]:
        raise ExternalServiceError(
            service="nominatim",
            message="Geocoding service rejected the request",
            details={"status_code": 403},
        )

    svc = LocationIntelligenceService(
        geocoder=boom,
        catalog=AsyncMock(return_value=[]),
    )
    with pytest.raises(ExternalServiceError):
        await svc.search("Darjeeling")
