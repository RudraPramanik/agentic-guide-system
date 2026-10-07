"""Tests for destination resolve (search-first / hub HITL) and country filtering."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from src.destinations.ingest import poi_allowed_for_destination, stamp_poi_country
from src.destinations.models import Destination
from src.destinations.service import DestinationService
from src.geo.country import countries_match, country_from_tags, normalize_country
from src.geo.geocoder import is_city_scale, is_oversized
from src.geo.schemas import GeocodedPlace, RawPOI


def _geo(**kwargs) -> GeocodedPlace:
    base = dict(
        name="X",
        lat=0.0,
        lng=0.0,
        osm_place_id="relation/1",
        country="IN",
        display_name="X",
    )
    base.update(kwargs)
    return GeocodedPlace(**base)


def test_normalize_and_match_country() -> None:
    assert normalize_country("in") == "IN"
    assert countries_match("IN", "in")
    assert not countries_match("IN", "NP")
    assert country_from_tags({"addr:country": "NP"}) == "NP"


def test_oversized_country_vs_city() -> None:
    japan = _geo(
        name="Japan",
        osm_class="boundary",
        osm_type_tag="administrative",
        addresstype="country",
        bbox_south=20.0,
        bbox_north=45.0,
        bbox_west=122.0,
        bbox_east=154.0,
        country="JP",
        osm_place_id="relation/japan",
    )
    darj = _geo(
        name="Darjeeling",
        osm_class="place",
        osm_type_tag="city",
        addresstype="city",
        bbox_south=26.9,
        bbox_north=27.2,
        bbox_west=88.1,
        bbox_east=88.4,
        osm_place_id="relation/darj",
    )
    assert is_oversized(japan)
    assert not is_oversized(darj)
    assert is_city_scale(darj)
    assert not is_city_scale(japan)


def test_poi_country_filter_drops_foreign() -> None:
    local = RawPOI(
        osm_id="node/1",
        name="Tea Estate",
        lat=27.0,
        lng=88.2,
        category="attraction",
        raw_tags={"addr:country": "IN"},
    )
    foreign = RawPOI(
        osm_id="node/2",
        name="Nepal Spot",
        lat=27.0,
        lng=88.1,
        category="attraction",
        raw_tags={"addr:country": "NP"},
    )
    untagged = RawPOI(
        osm_id="node/3",
        name="Unknown",
        lat=27.0,
        lng=88.2,
        category="attraction",
        raw_tags={},
    )
    assert poi_allowed_for_destination(local, "IN")
    assert not poi_allowed_for_destination(foreign, "IN")
    assert poi_allowed_for_destination(untagged, "IN")
    stamped = stamp_poi_country(local, "IN")
    assert stamped.raw_tags["wandr:country"] == "IN"


@pytest.mark.asyncio
async def test_resolve_city_destination(client, db_session, mocker) -> None:
    mocker.patch(
        "src.destinations.service.geocode_search",
        new=AsyncMock(
            return_value=[
                _geo(
                    name="Darjeeling",
                    lat=27.041,
                    lng=88.263,
                    osm_place_id=f"relation/darj-{uuid.uuid4().hex[:6]}",
                    country="IN",
                    display_name="Darjeeling, West Bengal, India",
                    osm_class="place",
                    osm_type_tag="city",
                    addresstype="city",
                    bbox_south=26.9,
                    bbox_north=27.2,
                    bbox_west=88.1,
                    bbox_east=88.4,
                )
            ]
        ),
    )

    response = await client.get("/api/v1/destinations/resolve?q=Darjeeling")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["kind"] == "destination"
    assert body["data"]["destination"]["name"] == "Darjeeling"


@pytest.mark.asyncio
async def test_resolve_country_returns_hubs(client, db_session, mocker) -> None:
    country = _geo(
        name="Japan",
        lat=35.0,
        lng=136.0,
        osm_place_id=f"relation/jp-{uuid.uuid4().hex[:6]}",
        country="JP",
        display_name="Japan",
        osm_class="boundary",
        osm_type_tag="administrative",
        addresstype="country",
        bbox_south=20.0,
        bbox_north=45.0,
        bbox_west=122.0,
        bbox_east=154.0,
    )
    tokyo = _geo(
        name="Tokyo",
        lat=35.68,
        lng=139.65,
        osm_place_id=f"relation/tyo-{uuid.uuid4().hex[:6]}",
        country="JP",
        display_name="Tokyo, Japan",
        osm_class="place",
        osm_type_tag="city",
        addresstype="city",
        bbox_south=35.5,
        bbox_north=35.8,
        bbox_west=139.5,
        bbox_east=139.9,
    )
    osaka = _geo(
        name="Osaka",
        lat=34.69,
        lng=135.50,
        osm_place_id=f"relation/osk-{uuid.uuid4().hex[:6]}",
        country="JP",
        display_name="Osaka, Japan",
        osm_class="place",
        osm_type_tag="city",
        addresstype="city",
        bbox_south=34.5,
        bbox_north=34.8,
        bbox_west=135.3,
        bbox_east=135.7,
    )

    async def fake_search(query, **kwargs):
        ft = kwargs.get("featuretype")
        if ft == "city":
            return [tokyo, osaka]
        return [country]

    mocker.patch(
        "src.destinations.service.geocode_search",
        new=AsyncMock(side_effect=fake_search),
    )

    response = await client.get("/api/v1/destinations/resolve?q=Japan")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["kind"] == "hubs"
    names = {h["name"] for h in body["data"]["hubs"]}
    assert "Tokyo" in names
    assert "Osaka" in names


@pytest.mark.asyncio
async def test_resolve_ambiguous_db_hits(client, db_session) -> None:
    for i, name in enumerate(("Springfield A", "Springfield B")):
        db_session.add(
            Destination(
                name=name,
                country="US",
                display_name=f"{name}, USA",
                osm_place_id=f"relation/sf-{i}-{uuid.uuid4().hex[:6]}",
                lat=40.0 + i,
                lng=-90.0,
                place_count=5,
            )
        )
    await db_session.flush()

    response = await client.get("/api/v1/destinations/resolve?q=Springfield")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["kind"] == "ambiguous"
    assert len(body["data"]["candidates"]) >= 2


@pytest.mark.asyncio
async def test_service_resolve_not_found(db_session, mocker) -> None:
    mocker.patch(
        "src.destinations.service.geocode_search",
        new=AsyncMock(return_value=[]),
    )
    svc = DestinationService(db_session)
    from src.destinations.exceptions import DestinationNotFoundError

    with pytest.raises(DestinationNotFoundError):
        await svc.resolve("ZzzNoPlace999")
