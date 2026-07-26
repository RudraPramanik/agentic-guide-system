"""Overpass gateway unit tests — mocked HTTP, no network."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from src.geo import overpass


@pytest.mark.asyncio
async def test_fetch_pois_deduplicates(mocker) -> None:
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": 27.04,
                "lon": 88.26,
                "tags": {"name": "First", "tourism": "museum"},
            },
            {
                "type": "node",
                "id": 1,
                "lat": 27.05,
                "lon": 88.27,
                "tags": {"name": "Last Wins", "tourism": "viewpoint"},
            },
            {
                "type": "node",
                "id": 2,
                "lat": 27.06,
                "lon": 88.28,
                "tags": {"tourism": "attraction"},
            },
        ]
    }
    mocker.patch.object(overpass, "_post_overpass", new=AsyncMock(return_value=payload))

    pois = await overpass.fetch_pois(27.041, 88.263, 30)

    by_id = {p.osm_id: p for p in pois}
    assert "node/1" in by_id
    assert by_id["node/1"].name == "Last Wins"
    assert by_id["node/1"].category == "viewpoint"
    assert "node/2" not in by_id


@pytest.mark.asyncio
async def test_fetch_pois_skips_unnamed_and_maps_way_center(mocker) -> None:
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 99,
                "center": {"lat": 27.1, "lon": 88.2},
                "tags": {"name": "Park Way", "leisure": "park"},
            },
            {
                "type": "node",
                "id": 3,
                "lat": 27.2,
                "lon": 88.3,
                "tags": {"tourism": "attraction"},
            },
        ]
    }
    mocker.patch.object(overpass, "_post_overpass", new=AsyncMock(return_value=payload))

    pois = await overpass.fetch_pois(27.041, 88.263, 10)

    assert len(pois) == 1
    assert pois[0].osm_id == "way/99"
    assert pois[0].category == "park"
    assert pois[0].lat == 27.1
    assert pois[0].lng == 88.2


@pytest.mark.asyncio
async def test_fetch_pois_radius_uses_meters(mocker) -> None:
    mock_post = AsyncMock(return_value={"elements": []})
    mocker.patch.object(overpass, "_post_overpass", new=mock_post)

    await overpass.fetch_pois(27.041, 88.263, 30)

    query = mock_post.await_args.args[0]
    assert "around:30000," in query


@pytest.mark.asyncio
async def test_fetch_pois_failure_returns_empty(mocker) -> None:
    mocker.patch.object(
        overpass,
        "_post_overpass",
        new=AsyncMock(side_effect=httpx.ConnectError("down")),
    )

    pois = await overpass.fetch_pois(27.041, 88.263, 30)

    assert pois == []
