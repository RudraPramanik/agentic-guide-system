"""Travel engine constants — structural vs interest vocabularies (data, not logic)."""

from __future__ import annotations

from uuid import UUID

MAX_PLACES_PER_DAY = 6
MIN_TRAVEL_BUFFER_MIN = 30
MAX_DAILY_TRAVEL_MIN = 180
DAY_START_TIME = "08:00"  # destination-local wall-clock; timezone-naive
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


def visit_duration_min(category: str) -> int:
    return VISIT_DURATION_BY_CATEGORY.get(category, VISIT_DURATION_DEFAULT_MIN)
