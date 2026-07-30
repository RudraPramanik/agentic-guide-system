"""Place selection — score and filter candidates (pure, no I/O).

AVOID_SAME_DAY_PAIRS greedy rule (keep-higher-score):
1. Score every candidate; sort descending by score, tie-break by (name, id).
2. Walk the sorted list and keep a candidate only if its structural category
   does not form a forbidden pair with any already-kept place
   (unordered match against AVOID_SAME_DAY_PAIRS, including same-category
   pairs such as monastery–monastery).
3. Because higher-scored places are considered first, conflicts drop the
   lower-scored candidate. Budget is soft-only and never hard-excludes.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from src.travel_engine.travel_rules import AVOID_SAME_DAY_PAIRS, CATEGORY_WEIGHTS


class PlaceCandidate(BaseModel):
    """Input place for selection — not the ORM Place model."""

    id: UUID
    name: str
    category: str
    enriched_tags: list[str] = Field(default_factory=list)
    lat: float
    lng: float


class TripPreferences(BaseModel):
    interests: list[str]
    budget: str | None = None  # soft only in P4
    days: int = 3


class ScoredPlace(BaseModel):
    place: PlaceCandidate
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)


def score_place(
    place: PlaceCandidate, interests: list[str]
) -> tuple[float, dict[str, float]]:
    """Sum CATEGORY_WEIGHTS for tags in both enriched_tags and interests."""
    interest_set = set(interests)
    breakdown: dict[str, float] = {}
    for tag in place.enriched_tags:
        if tag in CATEGORY_WEIGHTS and tag in interest_set:
            breakdown[tag] = CATEGORY_WEIGHTS[tag]
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
) -> list[ScoredPlace]:
    """
    Score, sort, and conflict-filter candidates.

    Budget on preferences is soft only — never hard-excludes.
    Empty candidates → []. Empty interests → all scores 0, still returned.
    """
    scored: list[ScoredPlace] = []
    for place in candidates:
        total, breakdown = score_place(place, preferences.interests)
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
