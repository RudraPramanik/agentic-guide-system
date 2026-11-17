"""Closed judgment schema. Invalid model output is not a score."""

from __future__ import annotations

from typing import Any

from src.evaluation.judge.dimensions import DIMENSIONS, PROMPT_VERSION, RUBRIC_VERSION


def parse_judgment(payload: Any) -> dict[str, Any] | None:
    """Return a normalized judgment, or None when the payload is not valid."""
    if not isinstance(payload, dict):
        return None
    model = payload.get("model")
    prompt_version = payload.get("prompt_version")
    rubric_version = payload.get("rubric_version")
    if not isinstance(model, str) or not model.strip():
        return None
    if prompt_version != PROMPT_VERSION or rubric_version != RUBRIC_VERSION:
        return None
    dimensions: dict[str, dict[str, Any]] = {}
    for name in DIMENSIONS:
        raw = payload.get(name)
        if not isinstance(raw, dict) or not isinstance(raw.get("passed"), bool):
            return None
        note = raw.get("note", "")
        if not isinstance(note, str):
            return None
        dimensions[name] = {"passed": raw["passed"], "note": note}
    return {
        "model": model.strip(),
        "prompt_version": prompt_version,
        "rubric_version": rubric_version,
        "dimensions": dimensions,
    }
