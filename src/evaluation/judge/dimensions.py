"""Shared preference and quality dimensions for the offline judge and human sheets."""

from __future__ import annotations

DIMENSIONS: tuple[str, ...] = ("relevance", "diversity", "narrative")
PROMPT_VERSION = "1"
RUBRIC_VERSION = "1"

PROMPT_TEXT = (
    "Score the itinerary on relevance, diversity, and narrative. "
    "Return JSON only. Each dimension is an object with passed (boolean) "
    "and note (string). Include model, prompt_version, and rubric_version. "
    "Do not invent a blended score."
)

RUBRIC_TEXT = (
    "relevance: the stops match the traveler request. "
    "diversity: the days are not the same kind of stop repeated. "
    "narrative: the day text describes the stops that were selected. "
    "Pass or fail each dimension. Free text is a note, not a score."
)
