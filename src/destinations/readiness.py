"""Pure destination readiness scoring — no I/O."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# Same distances as travel_rules.NORMALIZER_PROXIMITY_M and CLUSTER_RADIUS_KM.
# Kept local so this module does not import the travel engine.
READINESS_PROXIMITY_M = 150.0
READINESS_CLUSTER_KM = 10.0
PLANNER_DEFAULT_DAYS = 3
_EARTH_RADIUS_M = 6_371_000.0

PLACE_TARGET = 100

_SPARSE_MESSAGE = "Very limited POI data - results may be generic"
_LIMITED_MESSAGE = "Limited enrichment - semantic search not yet available"


@dataclass(frozen=True)
class ReadinessResult:
    score: float
    tier: Literal["ready", "limited", "sparse"]
    place_count: int
    enriched_pct: float
    indexed_pct: float
    message: str | None


def compute_readiness(
    place_count: int,
    enriched_count: int,
    indexed_count: int,
    search_available: bool,
) -> ReadinessResult:
    """
    Pure function — no I/O. Locked P2 formula from docs/steps/step2.md.
    Messages:
      sparse: "Very limited POI data - results may be generic"
      limited: "Limited enrichment - semantic search not yet available" (when enriched_pct < 0.5)
      ready: None
    """
    place_score = min(place_count / PLACE_TARGET, 1.0)
    enriched_pct = enriched_count / place_count if place_count > 0 else 0.0
    indexed_pct = (
        (indexed_count / place_count) if (place_count > 0 and search_available) else 0.0
    )

    score = round(0.4 * place_score + 0.35 * enriched_pct + 0.25 * indexed_pct, 3)
    tier: Literal["ready", "limited", "sparse"]
    if score >= 0.7:
        tier = "ready"
    elif score >= 0.3:
        tier = "limited"
    else:
        tier = "sparse"

    if tier == "sparse":
        message: str | None = _SPARSE_MESSAGE
    elif tier == "limited" and enriched_pct < 0.5:
        message = _LIMITED_MESSAGE
    else:
        message = None

    return ReadinessResult(
        score=score,
        tier=tier,
        place_count=place_count,
        enriched_pct=enriched_pct,
        indexed_pct=indexed_pct,
        message=message,
    )


@dataclass(frozen=True)
class ReadinessPlace:
    """Plain place row for Readiness V2. No ORM and no geometry type."""

    id: str
    name: str
    category: str | None
    lat: float
    lng: float
    source: str | None = None
    retrieved_at: datetime | None = None


def resolve_trip_days(days: int | None) -> int:
    """Generate day count. Omitted matches the planner default of 3."""
    if days is None:
        return PLANNER_DEFAULT_DAYS
    if days < 1 or days > 30:
        raise ValueError("days out of range")
    return days


def name_key(name: str) -> str:
    folded = name.casefold().strip()
    kept = [ch for ch in folded if ch.isalnum() or ch.isspace()]
    return " ".join("".join(kept).split())


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    arc = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(arc))


def coordinates_valid(lat: float, lng: float) -> bool:
    if not math.isfinite(lat) or not math.isfinite(lng):
        return False
    if lat < -90 or lat > 90 or lng < -180 or lng > 180:
        return False
    return not (lat == 0 and lng == 0)


def collapse_supply(places: list[ReadinessPlace]) -> list[ReadinessPlace]:
    """Collapse the same id, then the same name within 150 meters."""
    kept: list[ReadinessPlace] = []
    seen_ids: set[str] = set()
    for place in sorted(places, key=lambda item: str(item.id)):
        place_id = str(place.id)
        if place_id in seen_ids:
            continue
        key = name_key(place.name)
        if any(
            name_key(other.name) == key
            and haversine_m(place.lat, place.lng, other.lat, other.lng) <= READINESS_PROXIMITY_M
            for other in kept
        ):
            continue
        seen_ids.add(place_id)
        kept.append(place)
    return kept


def _clusters(places: list[ReadinessPlace]) -> list[list[ReadinessPlace]]:
    groups: list[list[ReadinessPlace]] = []
    for place in sorted(places, key=lambda item: str(item.id)):
        joined = False
        for group in groups:
            if any(
                haversine_m(place.lat, place.lng, member.lat, member.lng) / 1000
                <= READINESS_CLUSTER_KM
                for member in group
            ):
                group.append(place)
                joined = True
                break
        if not joined:
            groups.append([place])
    return groups


def _evidence_share(places: list[ReadinessPlace]) -> float:
    if not places:
        return 1.0
    ready = 0
    for place in places:
        if place.source and str(place.source).strip() and place.retrieved_at is not None:
            ready += 1
    return ready / len(places)


def compute_readiness_v2(
    places: list[ReadinessPlace],
    days: int,
    *,
    min_usable_per_day: int = 4,
    min_categories: int = 3,
    min_clusters_multi_day: int = 2,
    absolute_min_places: int = 10,
) -> ReadinessResult:
    """Distribution readiness. Pure. Does not replace compute_readiness."""
    if days < 1:
        raise ValueError("days out of range")

    coords_failed = any(
        not coordinates_valid(place.lat, place.lng) for place in places
    )
    valid = [place for place in places if coordinates_valid(place.lat, place.lng)]
    usable = collapse_supply(valid)
    usable_count = len(usable)
    need = days * min_usable_per_day
    categories = {
        place.category.strip()
        for place in usable
        if place.category and place.category.strip()
    }
    category_count = len(categories)
    groups = _clusters(usable) if usable else []
    cluster_count = len(groups)
    largest_share = (
        max(len(group) for group in groups) / usable_count if usable_count else 1.0
    )

    count_ok = usable_count >= need
    categories_ok = category_count >= min_categories
    if days > 1:
        spread_ok = (
            cluster_count >= min_clusters_multi_day and largest_share <= 0.70
        )
        if largest_share > 0.70:
            spread_ratio = 0.0
        else:
            spread_ratio = min(1.0, cluster_count / min_clusters_multi_day)
    else:
        spread_ok = True
        spread_ratio = 1.0
    coords_ok = not coords_failed

    below_floor = usable_count < absolute_min_places
    distribution_ok = count_ok and categories_ok and spread_ok and coords_ok
    if below_floor:
        tier: Literal["ready", "limited", "sparse"] = "sparse"
        score = round(min(0.299, (usable_count / absolute_min_places) * 0.299), 3)
    elif not distribution_ok:
        tier = "limited"
        ratios = [
            usable_count / need if need else 0.0,
            category_count / min_categories if min_categories else 0.0,
        ]
        if days > 1:
            ratios.append(spread_ratio)
        worst = 0.0 if not coords_ok else min(ratios)
        score = round(min(0.699, max(0.300, 0.300 + 0.399 * worst)), 3)
    else:
        tier = "ready"
        score = 1.0

    evidence = _evidence_share(usable)
    if tier == "ready":
        message: str | None = None
    else:
        parts: list[str] = []
        if below_floor:
            parts.append(f"usable places {usable_count} below {absolute_min_places}")
        else:
            if not count_ok:
                parts.append(
                    f"usable places {usable_count} for {days} days (need {need})"
                )
            if not categories_ok:
                parts.append(f"categories {category_count} (need {min_categories})")
            if days > 1 and not spread_ok:
                parts.append(f"{cluster_count} cluster (need {min_clusters_multi_day})")
            if not coords_ok:
                parts.append("invalid coordinates")
        prefix = "Sparse place supply" if tier == "sparse" else "Limited place supply"
        message = prefix + ": " + "; ".join(parts)
        if evidence < 1:
            message += f" Evidence share {evidence:.2f}."

    return ReadinessResult(
        score=score,
        tier=tier,
        place_count=usable_count,
        enriched_pct=0.0,
        indexed_pct=0.0,
        message=message,
    )
