"""Unit tests for travel_engine.travel_rules (step 4.9)."""

from __future__ import annotations

from src.places.constants import PLACE_TAG_VOCAB
from src.travel_engine.travel_rules import (
    CATEGORY_WEIGHTS,
    MAX_PLACES_PER_DAY,
    MAX_ROUTE_DROP_ATTEMPTS,
    MORNING_ONLY_CATEGORIES,
    VISIT_DURATION_BY_CATEGORY,
    VISIT_DURATION_DEFAULT_MIN,
    visit_duration_min,
)

_P2_CATEGORIES = {
    "museum",
    "viewpoint",
    "monastery",
    "attraction",
    "park",
    "trailhead",
}


def test_duration_keys_cover_p2_categories() -> None:
    assert _P2_CATEGORIES <= set(VISIT_DURATION_BY_CATEGORY)


def test_default_duration_for_unknown_category() -> None:
    assert visit_duration_min("unknown_future") == VISIT_DURATION_DEFAULT_MIN
    assert VISIT_DURATION_DEFAULT_MIN == 30


def test_category_weights_subset_of_place_tag_vocab() -> None:
    assert set(CATEGORY_WEIGHTS) <= set(PLACE_TAG_VOCAB)


def test_no_sunrise_point_in_morning_only() -> None:
    assert "sunrise_point" not in MORNING_ONLY_CATEGORIES
    assert MORNING_ONLY_CATEGORIES == ["viewpoint"]


def test_interest_only_tags_not_in_duration_map() -> None:
    for tag in ("trek", "cultural", "photography", "offbeat", "family", "nature", "adventure"):
        assert tag not in VISIT_DURATION_BY_CATEGORY


def test_drop_attempts_allow_thinning_full_day() -> None:
    assert MAX_ROUTE_DROP_ATTEMPTS == MAX_PLACES_PER_DAY - 1
