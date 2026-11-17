"""Async facade: geocoder + read-only catalog → resolution / search area."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.exceptions import ExternalServiceError
from src.destinations.repository import DestinationRepository
from src.geo.geocoder import geocode_search
from src.geo.schemas import GeocodedPlace
from src.location_intelligence.resolver import resolve_from_hits
from src.location_intelligence.schemas import (
    CatalogHit,
    LocationResolution,
    ResolvedLocation,
    SearchArea,
    SearchAreaPolicy,
)
from src.location_intelligence.search_area import build_search_area

GeocoderPort = Callable[[str], Awaitable[list[GeocodedPlace]]]
CatalogPort = Callable[[str], Awaitable[list[CatalogHit]]]


def _policy_from_settings() -> SearchAreaPolicy:
    settings = get_settings()
    return SearchAreaPolicy(
        poi_radius_km=settings.LOCATION_POI_RADIUS_KM,
        neighborhood_radius_km=settings.LOCATION_NEIGHBORHOOD_RADIUS_KM,
        city_fallback_radius_km=settings.LOCATION_CITY_FALLBACK_RADIUS_KM,
        max_radius_km=settings.LOCATION_MAX_RADIUS_KM,
    )


def _threshold_from_settings() -> float:
    return get_settings().LOCATION_AUTO_RESOLVE_CONFIDENCE


async def _default_geocoder(query: str) -> list[GeocodedPlace]:
    return await geocode_search(query, limit=5)


def _catalog_port_for_session(session: AsyncSession) -> CatalogPort:
    async def _read(query: str) -> list[CatalogHit]:
        rows = await DestinationRepository(session).search_by_name(query)
        return [
            CatalogHit(
                catalog_id=row.id,
                name=row.name,
                country=row.country,
                display_name=row.display_name,
                osm_place_id=row.osm_place_id,
                lat=row.lat,
                lng=row.lng,
            )
            for row in rows
        ]

    return _read


class LocationIntelligenceService:
    """Dark library entry point. Does not upsert destinations."""

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        geocoder: GeocoderPort | None = None,
        catalog: CatalogPort | None = None,
    ) -> None:
        self._geocoder = geocoder or _default_geocoder
        if catalog is not None:
            self._catalog = catalog
        elif session is not None:
            self._catalog = _catalog_port_for_session(session)
        else:

            async def _empty(_query: str) -> list[CatalogHit]:
                return []

            self._catalog = _empty

    async def search(self, query: str) -> LocationResolution:
        """Geocode + catalog merge + resolve. Timeout → not_found."""
        timeout = get_settings().SEARCH_GEOCODE_TIMEOUT_SECONDS
        try:
            hits = await asyncio.wait_for(self._geocoder(query), timeout=timeout)
        except TimeoutError:
            return LocationResolution(
                status="not_found",
                selected=None,
                candidates=[],
                requires_confirmation=False,
                reason="geocoder_timeout",
            )
        except ExternalServiceError:
            raise

        catalog_rows = await self._catalog(query)
        return resolve_from_hits(
            hits,
            catalog_rows,
            threshold=_threshold_from_settings(),
        )

    def search_area_for(
        self,
        anchor: ResolvedLocation,
        *,
        user_radius_km: float | None = None,
        polygon_geojson: dict[str, Any] | None = None,
        policy: SearchAreaPolicy | None = None,
    ) -> SearchArea:
        return build_search_area(
            anchor,
            policy or _policy_from_settings(),
            user_radius_km=user_radius_km,
            polygon_geojson=polygon_geojson,
        )
