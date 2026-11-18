"""Travel engine constants — structural vs interest vocabularies (data, not logic)."""

from __future__ import annotations

from uuid import UUID

MAX_PLACES_PER_DAY = 6
MIN_TRAVEL_BUFFER_MIN = 30
MAX_DAILY_TRAVEL_MIN = 180
DAY_START_TIME = "08:00"  # destination-local wall-clock; timezone-naive
DAY_END_TIME = "16:00"  # eight hours after DAY_START_TIME; naive wall-clock, no timezone
LUNCH_BREAK_START = "13:00"
LUNCH_BREAK_MIN = 60
MORNING_SLOT_LATEST_START = "10:30"
ACTIVE_DAY_VISIT_BUDGET_MIN = 8 * 60 - MIN_TRAVEL_BUFFER_MIN  # 450
CLUSTER_RADIUS_KM = 10.0
GEO_COHERENCE_MAX_STDDEV_KM = 15.0
ANCHOR_MIN_SCORE = 0.7
# Allow thinning a full day down to one stop when over travel budget.
MAX_ROUTE_DROP_ATTEMPTS = MAX_PLACES_PER_DAY - 1
BASE_SENTINEL_ID = UUID("00000000-0000-0000-0000-000000000000")

# ── STRUCTURAL — Place.category (P2) ──
VISIT_DURATION_BY_CATEGORY: dict[str, int] = {
    "monastery": 45,
    "viewpoint": 20,
    "museum": 60,
    "park": 30,
    "trailhead": 90,
    "attraction": 40,
    "cafe": 30,
    "restaurant": 60,
    "temple": 40,
    "historic": 40,
    "nature": 45,
}
VISIT_DURATION_DEFAULT_MIN = 30
MORNING_ONLY_CATEGORIES: list[str] = ["viewpoint"]
AVOID_SAME_DAY_PAIRS: list[tuple[str, str]] = [("monastery", "monastery")]

# ── INTEREST — Place.enriched_tags membership (P3 PLACE_TAG_VOCAB) ──
CATEGORY_WEIGHTS: dict[str, float] = {
    "photography": 1.4,
    "offbeat": 1.3,
    "viewpoint": 1.2,
    "trek": 1.1,
    "cultural": 1.0,
    "family": 0.9,
    "monastery": 1.0,
    "nature": 1.1,
    "adventure": 1.2,
}

# ── Slice 4.1 candidate normalizer (comparison keys / dedup thresholds) ──
NORMALIZER_PROXIMITY_M = 150.0
NORMALIZER_MERGE_CONFIDENCE = 0.85
# Per-rule confidences. A pair collapses only when its confidence is at or above
# NORMALIZER_MERGE_CONFIDENCE (exact id always clears).
NORMALIZER_CONF_EXACT_ID = 1.0
NORMALIZER_CONF_NAME_PROXIMITY = 0.92
NORMALIZER_CONF_ALIAS = 0.88
NORMALIZER_CONF_PARENT_CHILD = 0.86
# Tiny fixture-driven spelling variants (normalized name keys). Prefer candidate.aliases.
NORMALIZER_ALIAS_PAIRS: list[tuple[str, str]] = [
    ("ghoom monastery", "ghum monastery"),
]
CATEGORY_SYNONYMS: dict[str, str] = {
    "view point": "viewpoint",
    "view-point": "viewpoint",
}

# ── Slice 4.2 evidence-aware scoring (additive on v6.1 base; flag-gated) ──
# Conservative defaults for unit directionality only; do not raise without golden evidence.
SCORE_W_DIVERSITY = 0.15
SCORE_W_GEO_FIT = 0.10
SCORE_W_EVIDENCE = 0.05
SCORE_W_DUP_PENALTY = -0.25
SCORE_GEO_FIT_REF_KM = 5.0
SCORE_EVIDENCE_CAP = 3
SCORE_KEY_DIVERSITY = "diversity"
SCORE_KEY_GEO_FIT = "geo_fit"
SCORE_KEY_EVIDENCE = "evidence"
SCORE_KEY_DUP_PENALTY = "dup_penalty"
# Slice 7 reasoner boosts (injected map only). High stays below smallest interest weight.
SCORE_W_PRIORITY_HIGH = 0.30
SCORE_W_PRIORITY_MEDIUM = 0.15
SCORE_W_PRIORITY_LOW = 0.0
SCORE_KEY_REASONING_PRIORITY = "reasoning_priority"


def visit_duration_min(category: str) -> int:
    return VISIT_DURATION_BY_CATEGORY.get(category, VISIT_DURATION_DEFAULT_MIN)
