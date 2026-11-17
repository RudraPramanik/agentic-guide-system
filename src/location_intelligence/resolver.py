"""Candidate merge, classification, and resolution — pure functions."""

from __future__ import annotations

import math
import uuid

from src.geo.schemas import GeocodedPlace
from src.location_intelligence.confidence import (
    confidence_for,
    normalize_name,
    sort_key,
    within_km,
)
from src.location_intelligence.schemas import (
    CatalogHit,
    LocationResolution,
    LocationType,
    ResolvedLocation,
)

_MAX_CANDIDATES = 10
_OVERSIZED_BBOX_DEG = 1.1

_COUNTRY_TYPES = frozenset({"country"})
_REGION_TYPES = frozenset(
    {"state", "region", "province", "county", "state_district", "continent"}
)
_CITY_TYPES = frozenset({"city", "town", "village", "municipality"})
_NEIGHBORHOOD_TYPES = frozenset(
    {
        "suburb",
        "neighbourhood",
        "neighborhood",
        "quarter",
        "borough",
        "city_district",
        "hamlet",
    }
)
_CITY_SCALE_TYPES = _CITY_TYPES | _NEIGHBORHOOD_TYPES
_LANDMARK_NATURAL = frozenset({"peak", "volcano", "ridge", "cliff"})
_LANDMARK_TOURISM = frozenset({"attraction", "viewpoint"})
_POI_CLASSES = frozenset({"historic", "amenity", "building"})
_POI_TYPES = frozenset(
    {"monastery", "place_of_worship", "museum", "memorial", "ruins"}
)
_ADDRESS_TYPES = frozenset({"house", "isolated_dwelling", "address"})


def _country_code(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if len(text) == 2 and text.isalpha():
        return text.upper()
    return None


def _admin_area(display_name: str) -> str | None:
    parts = [p.strip() for p in display_name.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[1]
    return None


def _bbox(place: GeocodedPlace) -> list[float] | None:
    if None in (
        place.bbox_west,
        place.bbox_south,
        place.bbox_east,
        place.bbox_north,
    ):
        return None
    return [
        float(place.bbox_west),
        float(place.bbox_south),
        float(place.bbox_east),
        float(place.bbox_north),
    ]


def _is_oversized(place: GeocodedPlace) -> bool:
    """Mirror of geo.geocoder.is_oversized — kept local so this module stays pure."""
    addr = (place.addresstype or "").lower()
    if addr in _REGION_TYPES | _COUNTRY_TYPES:
        return True
    osm_class = (place.osm_class or "").lower()
    osm_type = (place.osm_type_tag or "").lower()
    if osm_class == "boundary" and osm_type in {"administrative", "political"}:
        if place.bbox_south is None:
            return addr in _REGION_TYPES | _COUNTRY_TYPES or addr == ""
    if None not in (
        place.bbox_south,
        place.bbox_north,
        place.bbox_west,
        place.bbox_east,
    ):
        lat_span = abs(place.bbox_north - place.bbox_south)  # type: ignore[operator]
        lng_span = abs(place.bbox_east - place.bbox_west)  # type: ignore[operator]
        mid_lat = (place.bbox_north + place.bbox_south) / 2.0  # type: ignore[operator]
        km_lat = lat_span * 111.0
        km_lng = lng_span * 111.0 * max(math.cos(math.radians(mid_lat)), 0.2)
        if (
            max(km_lat, km_lng) > 120.0
            or lat_span > _OVERSIZED_BBOX_DEG
            or lng_span > _OVERSIZED_BBOX_DEG
        ):
            return True
    return False


def _is_city_scale(place: GeocodedPlace) -> bool:
    if _is_oversized(place):
        return False
    addr = (place.addresstype or "").lower()
    osm_type = (place.osm_type_tag or "").lower()
    if addr in _CITY_SCALE_TYPES or osm_type in _CITY_SCALE_TYPES:
        return True
    if None not in (
        place.bbox_south,
        place.bbox_north,
        place.bbox_west,
        place.bbox_east,
    ):
        lat_span = abs(place.bbox_north - place.bbox_south)  # type: ignore[operator]
        lng_span = abs(place.bbox_east - place.bbox_west)  # type: ignore[operator]
        return lat_span <= _OVERSIZED_BBOX_DEG and lng_span <= _OVERSIZED_BBOX_DEG
    return not _is_oversized(place)


def classify_geocoded(place: GeocodedPlace) -> tuple[LocationType, str]:
    """Return (type, explanation). First matching rule wins. No network."""
    addr = (place.addresstype or "").lower()
    osm_class = (place.osm_class or "").lower()
    osm_type = (place.osm_type_tag or "").lower()

    if addr in _COUNTRY_TYPES:
        return LocationType.COUNTRY, "addresstype:country"
    if addr in _REGION_TYPES:
        return LocationType.REGION, f"addresstype:{addr}"
    if addr in _CITY_TYPES:
        return LocationType.CITY, f"addresstype:{addr}"
    if addr in _NEIGHBORHOOD_TYPES:
        return LocationType.NEIGHBORHOOD, f"addresstype:{addr}"
    if osm_class == "natural" and osm_type in _LANDMARK_NATURAL:
        return LocationType.LANDMARK, f"osm_class:natural+type:{osm_type}"
    if osm_class == "tourism" and osm_type in _LANDMARK_TOURISM:
        return LocationType.LANDMARK, f"osm_class:tourism+type:{osm_type}"
    if osm_class in _POI_CLASSES or osm_type in _POI_TYPES:
        detail = osm_class if osm_class in _POI_CLASSES else osm_type
        return LocationType.POI, f"poi:{detail}"
    if addr in _ADDRESS_TYPES:
        return LocationType.ADDRESS, f"addresstype:{addr}"
    if _is_city_scale(place) and not _is_oversized(place):
        return LocationType.CITY, "city_scale_fallback"
    return LocationType.POI, "default_poi"


def _find_catalog_match(
    *,
    osm_place_id: str | None,
    name: str,
    lat: float,
    lng: float,
    catalog_rows: list[CatalogHit],
    used: set[uuid.UUID],
) -> CatalogHit | None:
    for row in catalog_rows:
        if row.catalog_id in used:
            continue
        if osm_place_id and row.osm_place_id == osm_place_id:
            return row
    for row in catalog_rows:
        if row.catalog_id in used:
            continue
        if normalize_name(name) == normalize_name(row.name) and within_km(
            lat, lng, row.lat, row.lng
        ):
            return row
    return None


def _from_geocoded(
    place: GeocodedPlace,
    *,
    catalog: CatalogHit | None,
) -> ResolvedLocation:
    location_type, explanation = classify_geocoded(place)
    confidence = confidence_for(
        location_type,
        provider_id=place.osm_place_id,
        name=place.name,
        lat=place.lat,
        lng=place.lng,
        catalog=catalog,
    )
    return ResolvedLocation(
        canonical_name=place.name,
        location_type=location_type,
        lat=place.lat,
        lng=place.lng,
        country_code=_country_code(place.country),
        admin_area=_admin_area(place.display_name),
        provider="nominatim",
        provider_id=place.osm_place_id,
        confidence=confidence,
        bounding_box=_bbox(place),
        catalog_id=catalog.catalog_id if catalog else None,
        explanation=explanation,
    )


def _from_catalog(hit: CatalogHit) -> ResolvedLocation:
    # Catalog rows lack OSM class tags; treat named hubs as city for priors.
    location_type = LocationType.CITY
    explanation = "catalog:city_default"
    confidence = confidence_for(
        location_type,
        provider_id=hit.osm_place_id,
        name=hit.name,
        lat=hit.lat,
        lng=hit.lng,
        catalog=hit,
    )
    return ResolvedLocation(
        canonical_name=hit.name,
        location_type=location_type,
        lat=hit.lat,
        lng=hit.lng,
        country_code=_country_code(hit.country),
        admin_area=_admin_area(hit.display_name),
        provider="catalog",
        provider_id=hit.osm_place_id,
        confidence=confidence,
        bounding_box=None,
        catalog_id=hit.catalog_id,
        explanation=explanation,
    )


def normalize_candidates(
    geocoder_hits: list[GeocodedPlace],
    catalog_rows: list[CatalogHit],
) -> list[ResolvedLocation]:
    """Merge hits. Deterministic for the same inputs. Cap 10. No writes."""
    candidates: list[ResolvedLocation] = []
    seen_osm: set[str] = set()
    used_catalog: set[uuid.UUID] = set()

    for place in geocoder_hits:
        if place.osm_place_id in seen_osm:
            continue
        catalog = _find_catalog_match(
            osm_place_id=place.osm_place_id,
            name=place.name,
            lat=place.lat,
            lng=place.lng,
            catalog_rows=catalog_rows,
            used=used_catalog,
        )
        if catalog is not None:
            used_catalog.add(catalog.catalog_id)
        candidates.append(_from_geocoded(place, catalog=catalog))
        seen_osm.add(place.osm_place_id)

    for row in catalog_rows:
        if row.catalog_id in used_catalog:
            continue
        if row.osm_place_id and row.osm_place_id in seen_osm:
            continue

        matched_existing = False
        for i, existing in enumerate(candidates):
            same_name = normalize_name(existing.canonical_name) == normalize_name(
                row.name
            )
            if same_name and within_km(existing.lat, existing.lng, row.lat, row.lng):
                # Attach catalog id and recompute confidence with the bump.
                confidence = confidence_for(
                    existing.location_type,
                    provider_id=existing.provider_id,
                    name=existing.canonical_name,
                    lat=existing.lat,
                    lng=existing.lng,
                    catalog=row,
                )
                provider = (
                    "nominatim" if existing.provider_id else "catalog"
                )
                candidates[i] = existing.model_copy(
                    update={
                        "catalog_id": row.catalog_id,
                        "confidence": confidence,
                        "provider": provider,
                    }
                )
                used_catalog.add(row.catalog_id)
                matched_existing = True
                break
        if matched_existing:
            continue

        candidates.append(_from_catalog(row))
        used_catalog.add(row.catalog_id)
        if row.osm_place_id:
            seen_osm.add(row.osm_place_id)

    candidates.sort(key=sort_key)
    return candidates[:_MAX_CANDIDATES]


def resolve_candidates(
    candidates: list[ResolvedLocation],
    *,
    threshold: float,
) -> LocationResolution:
    """Apply auto-resolve policy. Never substitutes a city for a miss."""
    if not candidates:
        return LocationResolution(
            status="not_found",
            selected=None,
            candidates=[],
            requires_confirmation=False,
            reason="empty",
        )

    above = [c for c in candidates if c.confidence >= threshold]
    if len(above) == 1:
        return LocationResolution(
            status="resolved",
            selected=above[0],
            candidates=list(candidates),
            requires_confirmation=False,
            reason=None,
        )

    return LocationResolution(
        status="ambiguous",
        selected=None,
        candidates=list(candidates),
        requires_confirmation=True,
        reason="requires_confirmation" if not above else "multiple_above_threshold",
    )


def resolve_from_hits(
    geocoder_hits: list[GeocodedPlace],
    catalog_rows: list[CatalogHit],
    *,
    threshold: float,
) -> LocationResolution:
    return resolve_candidates(
        normalize_candidates(geocoder_hits, catalog_rows),
        threshold=threshold,
    )
