"""Classification, merge, and resolution tests."""

from __future__ import annotations

import uuid

from src.geo.schemas import GeocodedPlace
from src.location_intelligence.resolver import (
    classify_geocoded,
    normalize_candidates,
    resolve_candidates,
    resolve_from_hits,
)
from src.location_intelligence.schemas import CatalogHit, LocationType


def test_darjeeling_classifies_as_city(darjeeling: GeocodedPlace) -> None:
    loc_type, explanation = classify_geocoded(darjeeling)
    assert loc_type == LocationType.CITY
    assert "city" in explanation


def test_tiger_hill_classifies_as_landmark(tiger_hill: GeocodedPlace) -> None:
    loc_type, explanation = classify_geocoded(tiger_hill)
    assert loc_type == LocationType.LANDMARK
    assert "peak" in explanation


def test_ghoom_monastery_classifies_as_poi(ghoom_monastery: GeocodedPlace) -> None:
    loc_type, explanation = classify_geocoded(ghoom_monastery)
    assert loc_type == LocationType.POI
    assert "historic" in explanation or "monastery" in explanation


def test_same_fixture_yields_same_candidates(
    darjeeling: GeocodedPlace,
    darjeeling_catalog: CatalogHit,
) -> None:
    a = normalize_candidates([darjeeling], [darjeeling_catalog])
    b = normalize_candidates([darjeeling], [darjeeling_catalog])
    assert a == b


def test_duplicate_osm_ids_collapse(
    darjeeling: GeocodedPlace,
    darjeeling_catalog: CatalogHit,
) -> None:
    result = normalize_candidates([darjeeling], [darjeeling_catalog])
    assert len(result) == 1
    assert result[0].provider == "nominatim"
    assert result[0].catalog_id == darjeeling_catalog.catalog_id
    assert result[0].confidence == 0.97  # 0.92 + 0.05 capped


def test_one_city_auto_resolves(darjeeling: GeocodedPlace) -> None:
    resolution = resolve_from_hits([darjeeling], [], threshold=0.90)
    assert resolution.status == "resolved"
    assert resolution.selected is not None
    assert resolution.selected.location_type == LocationType.CITY
    assert resolution.requires_confirmation is False


def test_landmark_below_threshold_stays_ambiguous(tiger_hill: GeocodedPlace) -> None:
    resolution = resolve_from_hits([tiger_hill], [], threshold=0.90)
    assert resolution.status == "ambiguous"
    assert resolution.selected is None
    assert resolution.requires_confirmation is True
    assert len(resolution.candidates) == 1
    assert resolution.candidates[0].location_type == LocationType.LANDMARK
    assert resolution.candidates[0].confidence == 0.86


def test_two_cities_above_threshold_ambiguous() -> None:
    a = GeocodedPlace(
        name="Alpha",
        lat=27.0,
        lng=88.0,
        osm_place_id="relation/1",
        country="IN",
        display_name="Alpha, India",
        addresstype="city",
    )
    b = GeocodedPlace(
        name="Beta",
        lat=27.1,
        lng=88.1,
        osm_place_id="relation/2",
        country="IN",
        display_name="Beta, India",
        addresstype="city",
    )
    resolution = resolve_from_hits([a, b], [], threshold=0.90)
    assert resolution.status == "ambiguous"
    assert resolution.selected is None
    assert len(resolution.candidates) == 2


def test_empty_input_is_not_found() -> None:
    resolution = resolve_from_hits([], [], threshold=0.90)
    assert resolution.status == "not_found"
    assert resolution.selected is None
    assert resolution.requires_confirmation is False
    assert resolution.reason == "empty"


def test_resolve_candidates_direct() -> None:
    from src.location_intelligence.schemas import ResolvedLocation

    city = ResolvedLocation(
        canonical_name="X",
        location_type=LocationType.CITY,
        lat=1.0,
        lng=2.0,
        provider="nominatim",
        provider_id="relation/1",
        confidence=0.92,
        explanation="addresstype:city",
    )
    out = resolve_candidates([city], threshold=0.90)
    assert out.status == "resolved"
    assert out.selected == city
