"""Multi-source places facade — unions configured POI providers into RawPOI lists."""

from __future__ import annotations

import math
import re

from src.config import get_settings
from src.core.observability.logging import get_logger
from src.geo.geoapify_places import fetch_geoapify_pois
from src.geo.opentripmap import fetch_opentripmap_pois
from src.geo.overpass import fetch_pois
from src.geo.schemas import RawPOI

logger = get_logger(__name__)

_NEAR_DUP_METERS = 75.0


def _parse_sources(raw: str) -> list[str]:
    parts = [p.strip().lower() for p in (raw or "").split(",")]
    return [p for p in parts if p]


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _is_osm_id(osm_id: str) -> bool:
    return osm_id.startswith("node/") or osm_id.startswith("way/") or osm_id.startswith(
        "relation/"
    )


def dedupe_pois(pois: list[RawPOI]) -> list[RawPOI]:
    """Exact osm_id first; then near-dup by name + distance; prefer OSM ids."""
    by_id: dict[str, RawPOI] = {}
    for poi in pois:
        existing = by_id.get(poi.osm_id)
        if existing is None or _is_osm_id(poi.osm_id):
            by_id[poi.osm_id] = poi

    kept: list[RawPOI] = []
    for poi in by_id.values():
        norm = _normalize_name(poi.name)
        duplicate_of: RawPOI | None = None
        for other in kept:
            if _normalize_name(other.name) != norm:
                continue
            if _haversine_m(poi.lat, poi.lng, other.lat, other.lng) > _NEAR_DUP_METERS:
                continue
            duplicate_of = other
            break
        if duplicate_of is None:
            kept.append(poi)
            continue
        # Prefer OSM when colliding with a foreign id
        if _is_osm_id(poi.osm_id) and not _is_osm_id(duplicate_of.osm_id):
            kept[kept.index(duplicate_of)] = poi
    return kept


async def fetch_destination_pois(
    lat: float,
    lng: float,
    radius_km: float,
) -> list[RawPOI]:
    """
    Public ingest entry point for prepare/seed.
    Unions enabled PLACES_SOURCES; fail-soft per source; dedupes before return.
    """
    settings = get_settings()
    sources = _parse_sources(settings.PLACES_SOURCES)
    if not sources:
        sources = ["overpass"]

    # Resolve at call time so tests can patch module-level fetchers.
    source_fetchers = {
        "overpass": fetch_pois,
        "opentripmap": fetch_opentripmap_pois,
        "geoapify": fetch_geoapify_pois,
    }

    combined: list[RawPOI] = []
    for source in sources:
        fetcher = source_fetchers.get(source)
        if fetcher is None:
            logger.warning("places_unknown_source", source=source)
            continue
        try:
            batch = await fetcher(lat, lng, radius_km)
        except Exception as exc:  # noqa: BLE001 — one source must not abort the union
            logger.warning(
                "places_source_failed",
                source=source,
                error=type(exc).__name__,
            )
            batch = []
        logger.info(
            "places_source_fetched",
            source=source,
            count=len(batch),
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        )
        combined.extend(batch)

    return dedupe_pois(combined)
