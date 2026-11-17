"""Human-review sheet validation. No LLM call."""

from __future__ import annotations

from typing import Any

from src.evaluation.judge.dimensions import DIMENSIONS, RUBRIC_VERSION


def validate_review_sheet(payload: Any) -> list[str]:
    """Return error strings. An empty list means the sheet is valid."""
    if not isinstance(payload, dict):
        return ["not_an_object"]
    errors: list[str] = []
    if payload.get("rubric_version") != RUBRIC_VERSION:
        errors.append("missing_rubric_version")
    if not isinstance(payload.get("reviewer_id"), str) or not payload["reviewer_id"].strip():
        errors.append("missing_reviewer_id")
    if not isinstance(payload.get("case_id"), str) or not payload["case_id"].strip():
        errors.append("missing_case_id")
    if not isinstance(payload.get("free_text"), str):
        errors.append("missing_free_text")
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        errors.append("missing_dimensions")
        return errors
    for name in DIMENSIONS:
        raw = dimensions.get(name)
        if not isinstance(raw, dict) or not isinstance(raw.get("passed"), bool):
            errors.append(f"missing_dimension:{name}")
    extra = set(dimensions) - set(DIMENSIONS)
    if extra:
        errors.append("unknown_dimension")
    return errors
