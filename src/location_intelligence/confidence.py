"""Type priors and catalog confidence bumps — pure functions."""

from __future__ import annotations

import math

from src.location_intelligence.schemas import CatalogHit, LocationType, ResolvedLocation

_TYPE_PRIORS: dict[LocationType, float] = {
    LocationType.CITY: 0.92,
    LocationType.NEIGHBORHOOD: 0.88,
    LocationType.LANDMARK: 0.86,
    LocationType.POI: 0.84,
    LocationType.ADDRESS: 0.80,
    LocationType.COUNTRY: 0.70,
    LocationType.REGION: 0.70,
    LocationType.MAP_PIN: 0.80,
}

_CONFIDENCE_CAP = 0.97
_OSM_BUMP = 0.05
_NAME_BUMP = 0.04
_NAME_MATCH_KM = 1.0


def normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def within_km(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
    *,
    km: float = _NAME_MATCH_KM,
) -> bool:
    return haversine_km(lat1, lng1, lat2, lng2) <= km


def type_prior(location_type: LocationType) -> float:
    return _TYPE_PRIORS[location_type]


def apply_catalog_bump(
    prior: float,
    *,
    provider_id: str | None,
    name: str,
    lat: float,
    lng: float,
    catalog: CatalogHit | None,
) -> float:
    """Apply OSM-id or same-name-within-1km bump. Cap at 0.97."""
    if catalog is None:
        return prior
    score = prior
    if provider_id and catalog.osm_place_id and provider_id == catalog.osm_place_id:
        score = min(_CONFIDENCE_CAP, score + _OSM_BUMP)
    elif normalize_name(name) == normalize_name(catalog.name) and within_km(
        lat, lng, catalog.lat, catalog.lng
    ):
        score = min(_CONFIDENCE_CAP, score + _NAME_BUMP)
    return score


def confidence_for(
    location_type: LocationType,
    *,
    provider_id: str | None,
    name: str,
    lat: float,
    lng: float,
    catalog: CatalogHit | None,
) -> float:
    return apply_catalog_bump(
        type_prior(location_type),
        provider_id=provider_id,
        name=name,
        lat=lat,
        lng=lng,
        catalog=catalog,
    )


def sort_key(candidate: ResolvedLocation) -> tuple[float, str]:
    """Sort by confidence descending, then canonical name ascending."""
    return (-candidate.confidence, candidate.canonical_name.lower())
