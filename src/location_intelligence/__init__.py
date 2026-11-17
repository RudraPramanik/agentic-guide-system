"""Deterministic location candidates, resolution, and search areas (Slice 3)."""

from src.location_intelligence.schemas import (
    CatalogHit,
    LocationResolution,
    LocationType,
    ResolvedLocation,
    SearchArea,
    SearchAreaPolicy,
)
from src.location_intelligence.service import LocationIntelligenceService

__all__ = [
    "CatalogHit",
    "LocationIntelligenceService",
    "LocationResolution",
    "LocationType",
    "ResolvedLocation",
    "SearchArea",
    "SearchAreaPolicy",
]
