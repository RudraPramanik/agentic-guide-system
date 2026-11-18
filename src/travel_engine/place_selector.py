"""Place selection — score and filter candidates (pure, no I/O).

AVOID_SAME_DAY_PAIRS greedy rule (keep-higher-score):
1. Score every candidate; sort descending by score, tie-break by (name, id).
2. Walk the sorted list and keep a candidate only if its structural category
   does not form a forbidden pair with any already-kept place
   (unordered match against AVOID_SAME_DAY_PAIRS, including same-category
   pairs such as monastery–monastery).
3. Because higher-scored places are considered first, conflicts drop the
   lower-scored candidate. Budget is soft-only and never hard-excludes.

V2 scoring (injected ``v2_enabled`` only — never reads settings) keeps the
v6.1 sum-of-matching-weights base and adds configured travel_rules terms.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.travel_engine.travel_rules import (
    AVOID_SAME_DAY_PAIRS,
    CATEGORY_WEIGHTS,
    SCORE_EVIDENCE_CAP,
    SCORE_GEO_FIT_REF_KM,
    SCORE_KEY_DIVERSITY,
    SCORE_KEY_DUP_PENALTY,
    SCORE_KEY_EVIDENCE,
    SCORE_KEY_GEO_FIT,
    SCORE_KEY_REASONING_PRIORITY,
    SCORE_W_DIVERSITY,
    SCORE_W_DUP_PENALTY,
    SCORE_W_EVIDENCE,
    SCORE_W_GEO_FIT,
    SCORE_W_PRIORITY_HIGH,
    SCORE_W_PRIORITY_LOW,
    SCORE_W_PRIORITY_MEDIUM,
)

PriorityLevel = Literal["high", "medium", "low"]

_PRIORITY_WEIGHTS: dict[str, float] = {
    "high": SCORE_W_PRIORITY_HIGH,
    "medium": SCORE_W_PRIORITY_MEDIUM,
    "low": SCORE_W_PRIORITY_LOW,
}


def _priority_boost(level: str | None) -> float:
    if level is None:
        return 0.0
    return float(_PRIORITY_WEIGHTS.get(level, 0.0))


class PlaceCandidate(BaseModel):
    """Input place for selection — not the ORM Place model."""

    id: UUID
    name: str
    category: str
    enriched_tags: list[str] = Field(default_factory=list)
    lat: float
    lng: float
    user_selected: bool = False
    aliases: list[str] = Field(default_factory=list)
    parent_place_id: UUID | None = None
    source: str | None = None
    source_id: str | None = None
    evidence_count: int = 0
    # Optional hours. Default unknown. Scoring ignores these. No OSM parser here.
    opening_hours_status: Literal["verified", "unknown", "malformed"] = "unknown"
    opening_open: str | None = None
    opening_close: str | None = None
    opening_hours_raw: str | None = None


class TripPreferences(BaseModel):
    interests: list[str]
    budget: str | None = None  # soft only in P4
    days: int = 3


class ScoredPlace(BaseModel):
    place: PlaceCandidate
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)


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


def score_place(
    place: PlaceCandidate,
    interests: list[str],
    *,
    v2_enabled: bool = False,
    base_lat: float | None = None,
    base_lng: float | None = None,
    category_freq: dict[str, int] | None = None,
    apply_dup_penalty: bool = False,
) -> tuple[float, dict[str, float]]:
    """Sum CATEGORY_WEIGHTS for tags in both enriched_tags and interests.

    With ``v2_enabled``, add configured diversity / geo-fit / evidence /
    dup-penalty terms from travel_rules. Missing evidence contributes 0.
    """
    interest_set = set(interests)
    breakdown: dict[str, float] = {}
    for tag in place.enriched_tags:
        if tag in CATEGORY_WEIGHTS and tag in interest_set:
            breakdown[tag] = CATEGORY_WEIGHTS[tag]

    if v2_enabled:
        freq = category_freq or {}
        cat_n = max(1, freq.get(place.category, 1))
        diversity_term = 1.0 / float(cat_n)
        breakdown[SCORE_KEY_DIVERSITY] = round(SCORE_W_DIVERSITY * diversity_term, 4)

        if base_lat is not None and base_lng is not None:
            d_km = _haversine_km(place.lat, place.lng, base_lat, base_lng)
            geo_term = max(0.0, 1.0 - (d_km / SCORE_GEO_FIT_REF_KM))
            breakdown[SCORE_KEY_GEO_FIT] = round(SCORE_W_GEO_FIT * geo_term, 4)
        else:
            breakdown[SCORE_KEY_GEO_FIT] = 0.0

        capped = min(max(0, place.evidence_count), SCORE_EVIDENCE_CAP)
        evidence_term = (
            capped / float(SCORE_EVIDENCE_CAP) if SCORE_EVIDENCE_CAP else 0.0
        )
        breakdown[SCORE_KEY_EVIDENCE] = round(SCORE_W_EVIDENCE * evidence_term, 4)

        if apply_dup_penalty:
            breakdown[SCORE_KEY_DUP_PENALTY] = SCORE_W_DUP_PENALTY
        else:
            breakdown[SCORE_KEY_DUP_PENALTY] = 0.0

    return float(sum(breakdown.values())), breakdown


def explain_selection(
    place: PlaceCandidate, score_breakdown: dict[str, float]
) -> str:
    """
    Compact one-liner for tool_trace, e.g.
    "Tiger Hill score=2.6 [photography=1.4, viewpoint=1.2]"
    """
    total = sum(score_breakdown.values())
    parts = ", ".join(f"{tag}={weight}" for tag, weight in score_breakdown.items())
    return f"{place.name} score={total} [{parts}]"


def _categories_conflict(cat_a: str, cat_b: str) -> bool:
    for left, right in AVOID_SAME_DAY_PAIRS:
        if left == right:
            if cat_a == left and cat_b == left:
                return True
        elif {cat_a, cat_b} == {left, right}:
            return True
    return False


def _conflicts_with_kept(category: str, kept: list[ScoredPlace]) -> bool:
    return any(_categories_conflict(category, s.place.category) for s in kept)


def select_places(
    candidates: list[PlaceCandidate],
    preferences: TripPreferences,
    *,
    v2_enabled: bool = False,
    base_lat: float | None = None,
    base_lng: float | None = None,
    priorities: Mapping[UUID, PriorityLevel] | None = None,
) -> list[ScoredPlace]:
    """
    Score, sort, and conflict-filter candidates.

    Budget on preferences is soft only — never hard-excludes.
    Empty candidates → []. Empty interests → all scores 0, still returned.
    ``v2_enabled`` is injected; this module never reads settings.
    ``priorities`` is an optional injected map; None or {} leave scores unchanged.
    """
    priority_map = priorities or {}
    freq = Counter(c.category for c in candidates) if v2_enabled else {}
    name_counts: Counter[str] = Counter()
    name_key = None
    if v2_enabled:
        from src.travel_engine.candidate_normalizer import normalize_name_key

        name_key = normalize_name_key
        for c in candidates:
            name_counts[name_key(c.name)] += 1

    scored: list[ScoredPlace] = []
    for place in candidates:
        apply_dup = bool(
            name_key is not None
            and name_counts.get(name_key(place.name), 0) > 1
            and not place.user_selected
        )
        total, breakdown = score_place(
            place,
            preferences.interests,
            v2_enabled=v2_enabled,
            base_lat=base_lat,
            base_lng=base_lng,
            category_freq=dict(freq) if v2_enabled else None,
            apply_dup_penalty=apply_dup,
        )
        level = priority_map.get(place.id)
        if level is not None:
            boost = _priority_boost(level)
            breakdown = {**breakdown, SCORE_KEY_REASONING_PRIORITY: boost}
            total = float(sum(breakdown.values()))
        scored.append(
            ScoredPlace(place=place, score=total, score_breakdown=breakdown)
        )

    scored.sort(key=lambda s: (-s.score, s.place.name, str(s.place.id)))

    kept: list[ScoredPlace] = []
    for item in scored:
        if _conflicts_with_kept(item.place.category, kept):
            continue
        kept.append(item)
    return kept


def rank_candidates(
    candidates: list[PlaceCandidate],
    preferences: TripPreferences,
    *,
    v2_enabled: bool = False,
    base_lat: float | None = None,
    base_lng: float | None = None,
    priorities: Mapping[UUID, PriorityLevel] | None = None,
) -> list[ScoredPlace]:
    """Normalize (when V2) then select — shared entry for planner tools."""
    pool = candidates
    if v2_enabled:
        from src.travel_engine.candidate_normalizer import normalize_candidates

        pool = normalize_candidates(candidates)
    return select_places(
        pool,
        preferences,
        v2_enabled=v2_enabled,
        base_lat=base_lat,
        base_lng=base_lng,
        priorities=priorities,
    )
