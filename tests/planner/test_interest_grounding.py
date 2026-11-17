"""Catalog words in the traveler's text become interests."""

from __future__ import annotations

from src.planner.graph.nodes.parse_preferences import (
    _ground_interests,
    _normalize_interests,
)


def test_sunrise_maps_to_viewpoint() -> None:
    assert _normalize_interests(["sunrise"]) == ["viewpoint"]


def test_raw_text_keeps_photography_when_the_model_names_a_place() -> None:
    grounded = _ground_interests(
        "3 days photography sunrise Tiger Hill",
        ["Tiger Hill"],
    )
    assert "photography" in grounded
    assert "viewpoint" in grounded
    assert "Tiger Hill" in grounded


def test_unmatched_phrase_is_left_alone() -> None:
    assert _ground_interests("relaxed 3 days mid budget", ["relaxation"]) == [
        "relaxation"
    ]
