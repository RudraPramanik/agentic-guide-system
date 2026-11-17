"""Search-area policy tests."""

from __future__ import annotations

import pytest

from src.geo.schemas import GeocodedPlace
from src.location_intelligence.exceptions import (
    InvalidPolygonError,
    OversizedAdminError,
)
from src.location_intelligence.resolver import normalize_candidates
from src.location_intelligence.schemas import (
    LocationType,
    ResolvedLocation,
    SearchAreaPolicy,
)
from src.location_intelligence.search_area import build_search_area


def _anchor_from(place: GeocodedPlace) -> ResolvedLocation:
    return normalize_candidates([place], [])[0]


def test_city_boundary_vs_landmark_radius(
    darjeeling: GeocodedPlace,
    tiger_hill: GeocodedPlace,
    default_policy: SearchAreaPolicy,
) -> None:
    city_area = build_search_area(_anchor_from(darjeeling), default_policy)
    landmark_area = build_search_area(_anchor_from(tiger_hill), default_policy)

    assert city_area.strategy == "city_boundary"
    assert city_area.fallback_used is False
    assert city_area.radius_km is None
    assert city_area.boundary_geojson is not None
    assert city_area.boundary_geojson["type"] == "Polygon"

    assert landmark_area.strategy == "radius"
    assert landmark_area.radius_km == 10.0
    assert landmark_area.fallback_used is False


def test_city_missing_boundary_discloses_fallback(
    default_policy: SearchAreaPolicy,
) -> None:
    city = GeocodedPlace(
        name="NoBbox",
        lat=27.0,
        lng=88.0,
        osm_place_id="relation/9",
        country="IN",
        display_name="NoBbox, India",
        addresstype="city",
    )
    area = build_search_area(_anchor_from(city), default_policy)
    assert area.strategy == "radius"
    assert area.radius_km == 15.0
    assert area.fallback_used is True
    assert "15" in area.description


def test_map_pin_clamped_to_max(default_policy: SearchAreaPolicy) -> None:
    pin = ResolvedLocation(
        canonical_name="Pin",
        location_type=LocationType.MAP_PIN,
        lat=27.0,
        lng=88.0,
        provider="nominatim",
        provider_id=None,
        confidence=0.80,
        explanation="map_pin",
    )
    area = build_search_area(pin, default_policy, user_radius_km=80.0)
    assert area.radius_km == 50.0
    assert area.fallback_used is False
    assert "clamped" in area.description


def test_country_refuses_radius(default_policy: SearchAreaPolicy) -> None:
    country = ResolvedLocation(
        canonical_name="India",
        location_type=LocationType.COUNTRY,
        lat=20.0,
        lng=77.0,
        provider="nominatim",
        provider_id="relation/1",
        confidence=0.70,
        explanation="addresstype:country",
    )
    with pytest.raises(OversizedAdminError) as exc:
        build_search_area(country, default_policy)
    assert exc.value.code == "oversized_admin"


def test_region_refuses_radius(default_policy: SearchAreaPolicy) -> None:
    region = ResolvedLocation(
        canonical_name="West Bengal",
        location_type=LocationType.REGION,
        lat=23.0,
        lng=87.0,
        provider="nominatim",
        provider_id="relation/2",
        confidence=0.70,
        explanation="addresstype:state",
    )
    with pytest.raises(OversizedAdminError):
        build_search_area(region, default_policy)


def test_closed_polygon_accepted(default_policy: SearchAreaPolicy) -> None:
    pin = ResolvedLocation(
        canonical_name="Pin",
        location_type=LocationType.MAP_PIN,
        lat=27.0,
        lng=88.0,
        provider="nominatim",
        provider_id=None,
        confidence=0.80,
        explanation="map_pin",
    )
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [88.0, 27.0],
                [88.1, 27.0],
                [88.1, 27.1],
                [88.0, 27.1],
                [88.0, 27.0],
            ]
        ],
    }
    area = build_search_area(pin, default_policy, polygon_geojson=polygon)
    assert area.strategy == "polygon"
    assert area.fallback_used is False
    assert area.boundary_geojson == polygon


def test_open_ring_rejected(default_policy: SearchAreaPolicy) -> None:
    pin = ResolvedLocation(
        canonical_name="Pin",
        location_type=LocationType.MAP_PIN,
        lat=27.0,
        lng=88.0,
        provider="nominatim",
        provider_id=None,
        confidence=0.80,
        explanation="map_pin",
    )
    open_ring = {
        "type": "Polygon",
        "coordinates": [
            [
                [88.0, 27.0],
                [88.1, 27.0],
                [88.1, 27.1],
                [88.0, 27.1],
            ]
        ],
    }
    with pytest.raises(InvalidPolygonError) as exc:
        build_search_area(pin, default_policy, polygon_geojson=open_ring)
    assert exc.value.code == "invalid_polygon"
