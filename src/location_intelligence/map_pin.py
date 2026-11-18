"""Server-built map pin — never merged through the geocoder path."""

from __future__ import annotations

from src.location_intelligence.exceptions import InvalidCoordinatesError
from src.location_intelligence.schemas import LocationType, ResolvedLocation


def map_pin_location(
    lat: float,
    lng: float,
    *,
    canonical_name: str = "Map pin",
) -> ResolvedLocation:
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        raise InvalidCoordinatesError()
    return ResolvedLocation(
        canonical_name=canonical_name,
        location_type=LocationType.MAP_PIN,
        lat=float(lat),
        lng=float(lng),
        country_code=None,
        admin_area=None,
        provider="user",
        provider_id=None,
        confidence=1.0,
        bounding_box=None,
        boundary_geojson=None,
        catalog_id=None,
        explanation="user map pin",
    )
