"""Destinations HTTP router tests."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.middleware import rate_limit as rate_limit_module
from src.destinations.models import Destination
from src.geo.schemas import GeocodedPlace


@pytest.mark.asyncio
async def test_search_returns_list(client, db_session) -> None:
    dest = Destination(
        name="Searchable Town",
        country="IN",
        display_name="Searchable Town, India",
        osm_place_id=f"relation/search-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=10,
    )
    db_session.add(dest)
    await db_session.flush()

    response = await client.get("/api/v1/destinations/search?q=Searchable")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert body["data"][0]["name"] == "Searchable Town"


@pytest.mark.asyncio
async def test_search_not_found_404(client, mocker) -> None:
    mocker.patch(
        "src.destinations.service.geocode",
        new=AsyncMock(return_value=None),
    )

    response = await client.get("/api/v1/destinations/search?q=XyzzyNonexistent999")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "not_found"


@pytest.mark.asyncio
async def test_search_geocode_timeout_returns_404(client, mocker) -> None:
    async def hang(_query: str):
        await asyncio.sleep(30)

    mocker.patch("src.destinations.service.geocode", new=hang)
    mocker.patch(
        "src.destinations.service.get_settings",
        return_value=MagicMock(SEARCH_GEOCODE_TIMEOUT_SECONDS=0.05),
    )

    started = asyncio.get_running_loop().time()
    response = await client.get("/api/v1/destinations/search?q=SlowTownXX")
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 3.0
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "not_found"


@pytest.mark.asyncio
async def test_readiness_endpoint(client, db_session) -> None:
    dest = Destination(
        name="Ready Enough",
        country="IN",
        display_name="Ready Enough",
        osm_place_id=f"relation/ready-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=100,
        enriched_count=0,
        indexed_count=0,
    )
    db_session.add(dest)
    await db_session.flush()

    response = await client.get(f"/api/v1/destinations/{dest.id}/readiness")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tier"] == "limited"
    assert 0.35 <= data["score"] <= 0.45
    assert data["place_count"] == 100
    assert data["enriched_pct"] == 0.0
    assert data["indexed_pct"] == 0.0


@pytest.mark.asyncio
async def test_readiness_unknown_destination_404(client) -> None:
    response = await client.get(
        "/api/v1/destinations/00000000-0000-0000-0000-000000000001/readiness"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_search_rate_limit_is_path_specific(client, mocker) -> None:
    async def is_allowed(key: str, limit: int, window: int):
        if "/api/v1/destinations/search" in key:
            return False, 0
        return True, max(limit - 1, 0)

    mock_backend = MagicMock()
    mock_backend.is_allowed = AsyncMock(side_effect=is_allowed)
    mocker.patch.object(rate_limit_module, "get_rate_limiter", return_value=mock_backend)

    denied = await client.get("/api/v1/destinations/search?q=Darjeeling")
    health = await client.get("/api/v1/health")

    assert denied.status_code == 429
    assert denied.headers.get("x-ratelimit-limit") == "20"
    assert health.status_code == 200
