"""Shared fixtures for location-intelligence tests."""

from __future__ import annotations

import uuid

import pytest

from src.geo.schemas import GeocodedPlace
from src.location_intelligence.schemas import CatalogHit, SearchAreaPolicy


@pytest.fixture
def default_policy() -> SearchAreaPolicy:
    return SearchAreaPolicy(
        poi_radius_km=10.0,
        neighborhood_radius_km=5.0,
        city_fallback_radius_km=15.0,
        max_radius_km=50.0,
    )


@pytest.fixture
def darjeeling() -> GeocodedPlace:
    return GeocodedPlace(
        name="Darjeeling",
        lat=27.041,
        lng=88.263,
        osm_place_id="relation/123",
        country="IN",
        display_name="Darjeeling, West Bengal, India",
        addresstype="city",
        osm_class="place",
        osm_type_tag="city",
        bbox_south=27.0,
        bbox_north=27.1,
        bbox_west=88.2,
        bbox_east=88.3,
    )


@pytest.fixture
def tiger_hill() -> GeocodedPlace:
    return GeocodedPlace(
        name="Tiger Hill",
        lat=27.0,
        lng=88.3,
        osm_place_id="node/456",
        country="IN",
        display_name="Tiger Hill, Darjeeling, West Bengal, India",
        addresstype=None,
        osm_class="natural",
        osm_type_tag="peak",
    )


@pytest.fixture
def ghoom_monastery() -> GeocodedPlace:
    return GeocodedPlace(
        name="Ghoom Monastery",
        lat=27.0,
        lng=88.25,
        osm_place_id="way/789",
        country="IN",
        display_name="Ghoom Monastery, Darjeeling, West Bengal, India",
        addresstype=None,
        osm_class="historic",
        osm_type_tag="monastery",
    )


@pytest.fixture
def darjeeling_catalog() -> CatalogHit:
    return CatalogHit(
        catalog_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="Darjeeling",
        country="IN",
        display_name="Darjeeling, West Bengal, India",
        osm_place_id="relation/123",
        lat=27.041,
        lng=88.263,
    )
