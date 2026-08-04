"""Day allocation — pack scored places into per-day lists (pure, no I/O).

Places that cannot fit under MAX_PLACES_PER_DAY, ACTIVE_DAY_VISIT_BUDGET_MIN,
or the morning-only per-day cap (≤2) are omitted from the result (callers
observe this via returned list sizes).
"""

from __future__ import annotations

import math

from src.travel_engine.place_selector import ScoredPlace, TripPreferences
from src.travel_engine.travel_rules import (
    ACTIVE_DAY_VISIT_BUDGET_MIN,
    CLUSTER_RADIUS_KM,
    MAX_PLACES_PER_DAY,
    MORNING_ONLY_CATEGORIES,
    visit_duration_min,
)

_MAX_MORNING_ONLY_PER_DAY = 2


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


def _morning_count(day: list[ScoredPlace]) -> int:
    return sum(1 for s in day if s.place.category in MORNING_ONLY_CATEGORIES)


def _can_add(day: list[ScoredPlace], place: ScoredPlace) -> bool:
    if len(day) >= MAX_PLACES_PER_DAY:
        return False
    if (
        place.place.category in MORNING_ONLY_CATEGORIES
        and _morning_count(day) >= _MAX_MORNING_ONLY_PER_DAY
    ):
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


def _distance_to_day(day: list[ScoredPlace], place: ScoredPlace) -> float:
    """Soft geo distance for spill ranking.

    Empty days use CLUSTER_RADIUS_KM so an existing nearer day wins, but an
    empty day is preferred over joining a far centroid.
    """
    if not day:
        return CLUSTER_RADIUS_KM
    c_lat, c_lng = _cluster_centroid(day)
    return _haversine_km(place.place.lat, place.place.lng, c_lat, c_lng)


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
    - Each day: ≤2 places with category in MORNING_ONLY_CATEGORIES
    - Geographic pre-clustering: places within CLUSTER_RADIUS_KM prefer same day
    - Spill prefers nearer day centroid among days that can accept (soft geo)
    - Higher scores preferred when a day is full
    - Overflow that cannot fit any day is omitted (no logger; observe via sizes)

    ``preferences`` is accepted for API symmetry with callers; unused in packing.
    """
    _ = preferences  # reserved for future soft prefs; unused in packing
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
            # Soft geo spill: nearer centroid among days that can accept
            candidates = [di for di in range(days) if _can_add(day_lists[di], item)]
            if not candidates:
                continue  # omit overflow
            candidates.sort(
                key=lambda di: (
                    _distance_to_day(day_lists[di], item),
                    len(day_lists[di]),
                    di,
                )
            )
            day_lists[candidates[0]].append(item)

    return day_lists
