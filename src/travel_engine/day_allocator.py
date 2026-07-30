"""Day allocation — pack scored places into per-day lists (pure, no I/O).

Places that cannot fit under MAX_PLACES_PER_DAY or ACTIVE_DAY_VISIT_BUDGET_MIN
are omitted from the result (callers observe this via returned list sizes).
"""

from __future__ import annotations

import math

from src.travel_engine.place_selector import ScoredPlace, TripPreferences
from src.travel_engine.travel_rules import (
    ACTIVE_DAY_VISIT_BUDGET_MIN,
    CLUSTER_RADIUS_KM,
    MAX_PLACES_PER_DAY,
    visit_duration_min,
)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km (pure math; not a geo gateway)."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _day_visit_min(day: list[ScoredPlace]) -> int:
    return sum(visit_duration_min(s.place.category) for s in day)


def _can_add(day: list[ScoredPlace], place: ScoredPlace) -> bool:
    if len(day) >= MAX_PLACES_PER_DAY:
        return False
    return (
        _day_visit_min(day) + visit_duration_min(place.place.category)
        <= ACTIVE_DAY_VISIT_BUDGET_MIN
    )


def _cluster_centroid(cluster: list[ScoredPlace]) -> tuple[float, float]:
    n = len(cluster)
    lat = sum(s.place.lat for s in cluster) / n
    lng = sum(s.place.lng for s in cluster) / n
    return lat, lng


def _build_clusters(ordered: list[ScoredPlace]) -> list[list[ScoredPlace]]:
    """Greedy clusters: assign to first cluster whose centroid is within radius."""
    clusters: list[list[ScoredPlace]] = []
    for item in ordered:
        placed = False
        for cluster in clusters:
            c_lat, c_lng = _cluster_centroid(cluster)
            if (
                _haversine_km(item.place.lat, item.place.lng, c_lat, c_lng)
                <= CLUSTER_RADIUS_KM
            ):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters


def allocate_days(
    selected: list[ScoredPlace],
    days: int,
    preferences: TripPreferences | None = None,
) -> list[list[ScoredPlace]]:
    """
    Split scored places into exactly `days` lists.

    Rules:
    - Each day: len(places) <= MAX_PLACES_PER_DAY
    - Each day: sum(visit_duration_min(...)) <= ACTIVE_DAY_VISIT_BUDGET_MIN
    - Geographic pre-clustering: places within CLUSTER_RADIUS_KM prefer same day
    - Higher scores preferred when a day is full
    - Overflow that cannot fit any day is omitted (no logger; observe via sizes)

    ``preferences`` is accepted for API symmetry with callers; unused in P4 packing.
    """
    _ = preferences  # reserved for future soft prefs; unused in P4
    if days < 1:
        raise ValueError("days must be >= 1")

    day_lists: list[list[ScoredPlace]] = [[] for _ in range(days)]
    if not selected:
        return day_lists

    ordered = sorted(
        selected,
        key=lambda s: (-s.score, s.place.name, str(s.place.id)),
    )
    clusters = _build_clusters(ordered)
    # Prefer clusters with higher top score when assigning to days
    clusters.sort(
        key=lambda c: (-max(s.score for s in c), -len(c)),
    )

    for cluster in clusters:
        # Prefer the currently underfilled day (fewest places)
        preferred = min(range(days), key=lambda i: (len(day_lists[i]), i))
        for item in sorted(
            cluster,
            key=lambda s: (-s.score, s.place.name, str(s.place.id)),
        ):
            if _can_add(day_lists[preferred], item):
                day_lists[preferred].append(item)
                continue
            # Spill to other underfilled days (higher scores already tried preferred)
            placed = False
            day_order = sorted(range(days), key=lambda i: (len(day_lists[i]), i))
            for di in day_order:
                if _can_add(day_lists[di], item):
                    day_lists[di].append(item)
                    placed = True
                    break
            # else omit overflow

    return day_lists
