"""Location intelligence DTOs — pure data, no geocoder or repository imports."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class LocationType(StrEnum):
    COUNTRY = "country"
    REGION = "region"
    CITY = "city"
    NEIGHBORHOOD = "neighborhood"
    LANDMARK = "landmark"
    POI = "poi"
    ADDRESS = "address"
    MAP_PIN = "map_pin"


class CatalogHit(BaseModel):
    """Read-only destination catalog row used for merge and confidence bumps."""

    catalog_id: uuid.UUID
    name: str
    country: str
    display_name: str
    osm_place_id: str | None = None
    lat: float
    lng: float


class ResolvedLocation(BaseModel):
    canonical_name: str
    location_type: LocationType
    lat: float
    lng: float
    country_code: str | None = None
    admin_area: str | None = None
    provider: Literal["nominatim", "catalog", "user"]
    provider_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: list[float] | None = None  # [west, south, east, north]
    boundary_geojson: dict[str, Any] | None = None
    catalog_id: uuid.UUID | None = None
    explanation: str


class LocationResolution(BaseModel):
    status: Literal["resolved", "ambiguous", "not_found"]
    selected: ResolvedLocation | None = None
    candidates: list[ResolvedLocation] = Field(default_factory=list)
    requires_confirmation: bool = False
    reason: str | None = None


class SearchAreaPolicy(BaseModel):
    """Radius knobs filled from settings at the facade edge."""

    poi_radius_km: float = 10.0
    neighborhood_radius_km: float = 5.0
    city_fallback_radius_km: float = 15.0
    max_radius_km: float = 50.0


class SearchArea(BaseModel):
    strategy: Literal["city_boundary", "admin_boundary", "radius", "polygon"]
    anchor: ResolvedLocation
    radius_km: float | None = None
    boundary_geojson: dict[str, Any] | None = None
    fallback_used: bool = False
    description: str
