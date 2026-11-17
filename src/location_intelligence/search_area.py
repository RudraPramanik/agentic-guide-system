"""Search-area construction — pure functions."""

from __future__ import annotations

from typing import Any

from src.location_intelligence.exceptions import (
    InvalidPolygonError,
    OversizedAdminError,
)
from src.location_intelligence.schemas import (
    LocationType,
    ResolvedLocation,
    SearchArea,
    SearchAreaPolicy,
)


def _closed_bbox_polygon(bbox: list[float]) -> dict[str, Any]:
    """bbox is [west, south, east, north] → closed rectangular GeoJSON Polygon."""
    west, south, east, north = bbox
    ring = [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _validate_ring(ring: list[Any], *, path: str) -> None:
    if not isinstance(ring, list) or len(ring) < 4:
        raise InvalidPolygonError(f"{path}: ring must have at least four positions")
    first, last = ring[0], ring[-1]
    if not isinstance(first, (list, tuple)) or not isinstance(last, (list, tuple)):
        raise InvalidPolygonError(f"{path}: positions must be coordinate pairs")
    if len(first) < 2 or len(last) < 2:
        raise InvalidPolygonError(f"{path}: positions need longitude and latitude")
    if float(first[0]) != float(last[0]) or float(first[1]) != float(last[1]):
        raise InvalidPolygonError(f"{path}: ring is not closed")
    for i, pos in enumerate(ring):
        if not isinstance(pos, (list, tuple)) or len(pos) < 2:
            raise InvalidPolygonError(f"{path}[{i}]: bad position")
        lng, lat = float(pos[0]), float(pos[1])
        if not (-180.0 <= lng <= 180.0) or not (-90.0 <= lat <= 90.0):
            raise InvalidPolygonError(f"{path}[{i}]: coordinate out of range")


def validate_polygon_geojson(geometry: dict[str, Any]) -> dict[str, Any]:
    """Shape checks only — no self-intersection / shapely."""
    if not isinstance(geometry, dict):
        raise InvalidPolygonError("geometry must be an object")
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Polygon":
        if not isinstance(coords, list) or not coords:
            raise InvalidPolygonError("Polygon coordinates missing")
        for ri, ring in enumerate(coords):
            _validate_ring(ring, path=f"Polygon.ring[{ri}]")
        return geometry
    if gtype == "MultiPolygon":
        if not isinstance(coords, list) or not coords:
            raise InvalidPolygonError("MultiPolygon coordinates missing")
        for pi, poly in enumerate(coords):
            if not isinstance(poly, list) or not poly:
                raise InvalidPolygonError(f"MultiPolygon[{pi}] empty")
            for ri, ring in enumerate(poly):
                _validate_ring(ring, path=f"MultiPolygon[{pi}].ring[{ri}]")
        return geometry
    raise InvalidPolygonError(
        f"geometry type must be Polygon or MultiPolygon, got {gtype!r}"
    )


def build_search_area(
    anchor: ResolvedLocation,
    policy: SearchAreaPolicy,
    *,
    user_radius_km: float | None = None,
    polygon_geojson: dict[str, Any] | None = None,
) -> SearchArea:
    """Build a SearchArea per §6.3. Raises OversizedAdminError / InvalidPolygonError."""
    if polygon_geojson is not None:
        validated = validate_polygon_geojson(polygon_geojson)
        return SearchArea(
            strategy="polygon",
            anchor=anchor,
            radius_km=None,
            boundary_geojson=validated,
            fallback_used=False,
            description="supplied polygon",
        )

    if anchor.location_type in {LocationType.COUNTRY, LocationType.REGION}:
        raise OversizedAdminError(anchor.location_type.value)

    if anchor.location_type == LocationType.MAP_PIN:
        if user_radius_km is None:
            return SearchArea(
                strategy="radius",
                anchor=anchor,
                radius_km=policy.poi_radius_km,
                boundary_geojson=None,
                fallback_used=True,
                description=(
                    f"map pin with no radius; using {policy.poi_radius_km:g} km"
                ),
            )
        if user_radius_km > policy.max_radius_km:
            return SearchArea(
                strategy="radius",
                anchor=anchor,
                radius_km=policy.max_radius_km,
                boundary_geojson=None,
                fallback_used=False,
                description=(
                    f"map pin radius clamped from {user_radius_km:g} km "
                    f"to {policy.max_radius_km:g} km"
                ),
            )
        return SearchArea(
            strategy="radius",
            anchor=anchor,
            radius_km=user_radius_km,
            boundary_geojson=None,
            fallback_used=False,
            description=f"map pin radius {user_radius_km:g} km",
        )

    if anchor.location_type == LocationType.CITY:
        if anchor.bounding_box is not None:
            return SearchArea(
                strategy="city_boundary",
                anchor=anchor,
                radius_km=None,
                boundary_geojson=_closed_bbox_polygon(anchor.bounding_box),
                fallback_used=False,
                description="city bbox rectangle",
            )
        return SearchArea(
            strategy="radius",
            anchor=anchor,
            radius_km=policy.city_fallback_radius_km,
            boundary_geojson=None,
            fallback_used=True,
            description=(
                f"city boundary missing; radius "
                f"{policy.city_fallback_radius_km:g} km"
            ),
        )

    if anchor.location_type == LocationType.NEIGHBORHOOD:
        if anchor.bounding_box is not None:
            return SearchArea(
                strategy="admin_boundary",
                anchor=anchor,
                radius_km=None,
                boundary_geojson=_closed_bbox_polygon(anchor.bounding_box),
                fallback_used=False,
                description="neighborhood bbox rectangle",
            )
        return SearchArea(
            strategy="radius",
            anchor=anchor,
            radius_km=policy.neighborhood_radius_km,
            boundary_geojson=None,
            fallback_used=True,
            description=(
                f"neighborhood boundary missing; radius "
                f"{policy.neighborhood_radius_km:g} km"
            ),
        )

    if anchor.location_type in {LocationType.LANDMARK, LocationType.POI}:
        return SearchArea(
            strategy="radius",
            anchor=anchor,
            radius_km=policy.poi_radius_km,
            boundary_geojson=None,
            fallback_used=False,
            description=f"{anchor.location_type.value} radius {policy.poi_radius_km:g} km",
        )

    if anchor.location_type == LocationType.ADDRESS:
        return SearchArea(
            strategy="radius",
            anchor=anchor,
            radius_km=policy.neighborhood_radius_km,
            boundary_geojson=None,
            fallback_used=False,
            description=(
                f"address local radius {policy.neighborhood_radius_km:g} km"
            ),
        )

    # Defensive fallback — should not reach for known types.
    return SearchArea(
        strategy="radius",
        anchor=anchor,
        radius_km=policy.poi_radius_km,
        boundary_geojson=None,
        fallback_used=True,
        description=f"unknown type; radius {policy.poi_radius_km:g} km",
    )
