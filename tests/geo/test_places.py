"""Places facade unit tests — mocked sources, no network."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.geo import places
from src.geo.schemas import RawPOI


def _poi(osm_id: str, name: str, lat: float, lng: float, category: str = "attraction") -> RawPOI:
    return RawPOI(
        osm_id=osm_id,
        name=name,
        lat=lat,
        lng=lng,
        category=category,
        raw_tags={},
    )


def test_dedupe_exact_id_keeps_one() -> None:
    a = _poi("node/1", "A", 27.0, 88.0)
    b = _poi("node/1", "B", 27.1, 88.1)
    out = places.dedupe_pois([a, b])
    assert len(out) == 1
    assert out[0].name == "B"


def test_dedupe_near_prefers_osm() -> None:
    osm = _poi("node/9", "Glenary Cafe", 27.0410, 88.2630, "cafe")
    otm = _poi("otm:X1", "Glenary Cafe", 27.0411, 88.2631, "cafe")
    out = places.dedupe_pois([otm, osm])
    assert len(out) == 1
    assert out[0].osm_id == "node/9"


@pytest.mark.asyncio
async def test_facade_default_overpass_only(mocker) -> None:
    mocker.patch.object(
        places,
        "get_settings",
        return_value=type(
            "S",
            (),
            {"PLACES_SOURCES": "overpass"},
        )(),
    )
    mock_overpass = AsyncMock(return_value=[_poi("node/1", "A", 27.0, 88.0)])
    mock_otm = AsyncMock(return_value=[_poi("otm:1", "B", 27.1, 88.1)])
    mocker.patch.object(places, "fetch_pois", new=mock_overpass)
    mocker.patch.object(places, "fetch_opentripmap_pois", new=mock_otm)

    pois = await places.fetch_destination_pois(27.0, 88.0, 10)

    assert len(pois) == 1
    assert pois[0].osm_id == "node/1"
    mock_overpass.assert_awaited_once()
    mock_otm.assert_not_awaited()


@pytest.mark.asyncio
async def test_facade_missing_optional_still_returns_overpass(mocker) -> None:
    mocker.patch.object(
        places,
        "get_settings",
        return_value=type(
            "S",
            (),
            {"PLACES_SOURCES": "overpass,opentripmap"},
        )(),
    )
    mock_overpass = AsyncMock(return_value=[_poi("node/1", "A", 27.0, 88.0)])
    mock_otm = AsyncMock(return_value=[])  # missing key → []
    mocker.patch.object(places, "fetch_pois", new=mock_overpass)
    mocker.patch.object(places, "fetch_opentripmap_pois", new=mock_otm)

    pois = await places.fetch_destination_pois(27.0, 88.0, 10)

    assert len(pois) == 1
    mock_otm.assert_awaited_once()


@pytest.mark.asyncio
async def test_facade_one_source_failure_keeps_sibling(mocker) -> None:
    mocker.patch.object(
        places,
        "get_settings",
        return_value=type(
            "S",
            (),
            {"PLACES_SOURCES": "overpass,opentripmap"},
        )(),
    )
    mock_overpass = AsyncMock(return_value=[_poi("node/1", "A", 27.0, 88.0)])
    mock_otm = AsyncMock(side_effect=RuntimeError("boom"))
    mocker.patch.object(places, "fetch_pois", new=mock_overpass)
    mocker.patch.object(places, "fetch_opentripmap_pois", new=mock_otm)

    pois = await places.fetch_destination_pois(27.0, 88.0, 10)

    assert len(pois) == 1
    assert pois[0].osm_id == "node/1"
