"""Containment and covering-radius helpers."""

from __future__ import annotations

from src.location_intelligence.containment import (
    covering_radius_km,
    point_in_search_area,
)
from src.location_intelligence.schemas import (
    LocationType,
    ResolvedLocation,
    SearchArea,
)


def _anchor(**kwargs) -> ResolvedLocation:
    base = dict(
        canonical_name="A",
        location_type=LocationType.CITY,
        lat=27.0,
        lng=88.0,
        provider="catalog",
        provider_id="1",
        confidence=0.9,
        explanation="t",
    )
    base.update(kwargs)
    return ResolvedLocation(**base)


def test_radius_excludes_far_point() -> None:
    area = SearchArea(
        strategy="radius",
        anchor=_anchor(location_type=LocationType.LANDMARK),
        radius_km=10.0,
        fallback_used=False,
        description="10",
    )
    assert point_in_search_area(27.01, 88.01, area)
    assert not point_in_search_area(28.0, 89.0, area)


def test_bbox_ring_excludes_outside() -> None:
    ring = {
        "type": "Polygon",
        "coordinates": [
            [
                [88.0, 27.0],
                [88.1, 27.0],
                [88.1, 27.1],
                [88.0, 27.1],
                [88.0, 27.0],
            ]
        ],
    }
    area = SearchArea(
        strategy="city_boundary",
        anchor=_anchor(),
        radius_km=None,
        boundary_geojson=ring,
        fallback_used=False,
        description="bbox",
    )
    assert point_in_search_area(27.05, 88.05, area)
    assert not point_in_search_area(27.5, 88.5, area)
    # Inside covering circle of a larger query, still outside the ring.
    cover = covering_radius_km(ring, center_lat=27.05)
    assert cover > 0
    assert not point_in_search_area(27.05, 88.2, area)
