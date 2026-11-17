"""Pure evaluation metrics. No LLM, network, or database I/O.

Geographic coherence copies the definition in
``trip_validator._day_coord_stddev_km`` (local-km offsets, sample variance,
square root of the sum). This module does not import the validator.
"""

from __future__ import annotations

import math


def location_type_accuracy(predicted: list[str], labeled: list[str]) -> float:
    if not labeled:
        return 1.0
    matches = 0
    for index, label in enumerate(labeled):
        if index < len(predicted) and predicted[index] == label:
            matches += 1
    return matches / len(labeled)


def retrieval_recall_at_k(
    retrieved: list[str],
    labeled: list[str],
    k: int,
) -> float:
    distinct: list[str] = []
    seen: set[str] = set()
    for item in labeled:
        if item not in seen:
            seen.add(item)
            distinct.append(item)
    if not distinct:
        return 1.0
    top = set(retrieved[:k])
    hits = sum(1 for item in distinct if item in top)
    return hits / len(distinct)


def duplicate_stop_count(place_ids: list[str]) -> int:
    return len(place_ids) - len(set(place_ids))


def geographic_coherence_km(coords: list[tuple[float, float]]) -> float | None:
    """Kilometer dispersion. Lower is tighter. Fewer than two points has no score."""
    n = len(coords)
    if n < 2:
        return None
    mean_lat = sum(lat for lat, _lng in coords) / n
    mean_lng = sum(lng for _lat, lng in coords) / n
    cos_lat = math.cos(math.radians(mean_lat))
    north = [(lat - mean_lat) * 111.0 for lat, _lng in coords]
    east = [(lng - mean_lng) * 111.0 * cos_lat for _lat, lng in coords]
    mean_n = sum(north) / n
    mean_e = sum(east) / n
    var_n = sum((value - mean_n) ** 2 for value in north) / (n - 1)
    var_e = sum((value - mean_e) ** 2 for value in east) / (n - 1)
    return math.sqrt(var_n + var_e)


def schedule_feasibility(
    days: list[tuple[int, int]],
    active_cap: int,
    travel_cap: int,
) -> float:
    if not days:
        return 1.0
    fitting = 0
    for visit_min, travel_min in days:
        if visit_min <= active_cap and travel_min <= travel_cap:
            fitting += 1
    return fitting / len(days)


def preference_match(
    places: list[tuple[str, list[str]]],
    interests: list[str],
) -> float:
    if not places:
        return 1.0
    wanted = {item.strip().lower() for item in interests if item.strip()}
    hits = 0
    for category, tags in places:
        keys = {category.strip().lower()}
        keys.update(tag.strip().lower() for tag in tags if tag.strip())
        if keys & wanted:
            hits += 1
    return hits / len(places)


def persistence_match(generated: list[list[str]], saved: list[list[str]]) -> bool:
    return generated == saved


def map_itinerary_match(feature_ids: list[str], stop_ids: list[str]) -> bool:
    return list(feature_ids) == list(stop_ids)
