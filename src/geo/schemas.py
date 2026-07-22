"""Geo DTOs for Nominatim, Overpass, and OSRM gateways."""

from pydantic import BaseModel, Field


class GeocodedPlace(BaseModel):
    """Result of a successful Nominatim geocode."""

    name: str
    lat: float
    lng: float
    osm_place_id: str  # Nominatim osm_type/osm_id composite, e.g. "relation/123"
    country: str  # country_code uppercased, or country name if code missing
    display_name: str


class RawPOI(BaseModel):
    """Parsed Overpass element — used by overpass.py (step 2.2)."""

    osm_id: str  # "{type}/{id}"
    name: str
    lat: float
    lng: float
    category: str
    raw_tags: dict = Field(default_factory=dict)


class RouteResult(BaseModel):
    """OSRM route result — used by osrm.py (step 2.5)."""

    distance_km: float
    duration_min: float
    encoded_polyline: str | None = None
    fallback_used: bool = False
