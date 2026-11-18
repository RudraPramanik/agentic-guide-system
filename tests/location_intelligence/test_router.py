"""Location routes: 404 when flag off; envelope when on."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.location_intelligence.schemas import LocationResolution, LocationType, ResolvedLocation
from src.main import create_app


@pytest.fixture
def app():
    get_settings.cache_clear()
    application = create_app()
    yield application
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_locations_search_404_when_flag_off(app, monkeypatch):
    monkeypatch.setenv("LOCATION_V2_ENABLED", "false")
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "src.location_intelligence.service.LocationIntelligenceService.search",
            new_callable=AsyncMock,
        ) as search:
            resp = await client.post("/api/v1/locations/search", json={"query": "Darjeeling"})
            assert resp.status_code == 404
            search.assert_not_called()


@pytest.mark.asyncio
async def test_locations_search_ok_when_flag_on(app, monkeypatch):
    monkeypatch.setenv("LOCATION_V2_ENABLED", "true")
    get_settings.cache_clear()
    resolution = LocationResolution(
        status="resolved",
        selected=ResolvedLocation(
            canonical_name="Darjeeling",
            location_type=LocationType.CITY,
            lat=27.0,
            lng=88.0,
            provider="nominatim",
            provider_id="N1",
            confidence=0.92,
            explanation="city",
        ),
        candidates=[],
        requires_confirmation=False,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "src.location_intelligence.router.LocationIntelligenceService.search",
            new_callable=AsyncMock,
            return_value=resolution,
        ):
            resp = await client.post("/api/v1/locations/search", json={"query": "Darjeeling"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "resolved"
