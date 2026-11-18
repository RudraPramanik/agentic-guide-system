"""Pure point-in-search-area checks. No shapely, no I/O."""

from __future__ import annotations

import math
from typing import Any

from src.location_intelligence.confidence import haversine_km
from src.location_intelligence.schemas import SearchArea


def _point_in_ring(lng: float, lat: float, ring: list[Any]) -> bool:
    """Ray cast. Ring positions are [lng, lat]."""
    inside = False
    n = len(ring)
    if n < 4:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        intersects = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _point_in_geometry(lng: float, lat: float, geometry: dict[str, Any]) -> bool:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Polygon" and isinstance(coords, list) and coords:
        exterior = coords[0]
        if not _point_in_ring(lng, lat, exterior):
            return False
        for hole in coords[1:]:
            if _point_in_ring(lng, lat, hole):
                return False
        return True
    if gtype == "MultiPolygon" and isinstance(coords, list):
        for poly in coords:
            if not isinstance(poly, list) or not poly:
                continue
            exterior = poly[0]
            if not _point_in_ring(lng, lat, exterior):
                continue
            in_hole = False
            for hole in poly[1:]:
                if _point_in_ring(lng, lat, hole):
                    in_hole = True
                    break
            if not in_hole:
                return True
        return False
    return False


def covering_radius_km(boundary_geojson: dict[str, Any], *, center_lat: float) -> float:
    """Half the bounding-box diagonal in km — PostGIS prefilter only."""
    positions: list[tuple[float, float]] = []

    def _collect(ring: Any) -> None:
        if not isinstance(ring, list):
            return
        for pos in ring:
            if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                positions.append((float(pos[0]), float(pos[1])))

    gtype = boundary_geojson.get("type")
    coords = boundary_geojson.get("coordinates")
    if gtype == "Polygon" and isinstance(coords, list):
        for ring in coords:
            _collect(ring)
    elif gtype == "MultiPolygon" and isinstance(coords, list):
        for poly in coords:
            if isinstance(poly, list):
                for ring in poly:
                    _collect(ring)
    if not positions:
        return 0.0
    west = min(p[0] for p in positions)
    east = max(p[0] for p in positions)
    south = min(p[1] for p in positions)
    north = max(p[1] for p in positions)
    lat_span = abs(north - south)
    lng_span = abs(east - west)
    cos_lat = max(math.cos(math.radians(center_lat)), 0.2)
    half_diag = 0.5 * math.sqrt(
        (lat_span * 111.0) ** 2 + (lng_span * 111.0 * cos_lat) ** 2
    )
    return max(half_diag, 0.1)


def point_in_search_area(lat: float, lng: float, area: SearchArea) -> bool:
    """True when the point lies inside the stored geometry or radius."""
    if area.strategy == "radius":
        if area.radius_km is None:
            return False
        return (
            haversine_km(lat, lng, area.anchor.lat, area.anchor.lng) <= area.radius_km
        )
    if area.boundary_geojson is None:
        return False
    return _point_in_geometry(lng, lat, area.boundary_geojson)
