"""Fixture ingestion quality. No database and no network."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.destinations.readiness import ReadinessPlace, collapse_supply

FIXTURE_NAMES = ("darjeeling", "manali", "goa")


def _place(raw: dict) -> ReadinessPlace:
    return ReadinessPlace(
        id=str(raw.get("id") or ""),
        name=str(raw.get("name") or ""),
        category=raw.get("category"),
        lat=float(raw["lat"]),
        lng=float(raw["lng"]),
        source=raw.get("source"),
        retrieved_at=None,
    )


def _fresh(retrieved_at: object, as_of: date) -> bool:
    if not isinstance(retrieved_at, str) or retrieved_at.strip() == "":
        return False
    day = date.fromisoformat(retrieved_at[:10])
    delta = (as_of - day).days
    return 0 <= delta <= 30


def report_destination(payload: dict) -> dict:
    places = payload.get("places") or []
    if not isinstance(places, list):
        raise ValueError("places must be a list")
    as_of = date.fromisoformat(str(payload["as_of"]))
    rows = [_place(item) for item in places if isinstance(item, dict)]
    input_count = len(rows)
    usable = collapse_supply(rows)
    duplicate_rate = 0.0 if input_count == 0 else (input_count - len(usable)) / input_count
    categories: dict[str, int] = {}
    fresh = 0
    for item in places:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "")
        categories[category] = categories.get(category, 0) + 1
        if _fresh(item.get("retrieved_at"), as_of):
            fresh += 1
    failures = payload.get("failures") or []
    reasons = [
        str(item.get("reason"))
        for item in failures
        if isinstance(item, dict) and item.get("reason")
    ]
    freshness = 0.0 if input_count == 0 else fresh / input_count
    return {
        "destination": payload.get("destination"),
        "place_count": input_count,
        "category_distribution": categories,
        "duplicate_rate": duplicate_rate,
        "failure_count": len(reasons),
        "failures": reasons,
        "freshness_share": freshness,
    }


def load_fixture_dir(folder: Path) -> dict:
    sections = []
    for name in FIXTURE_NAMES:
        path = folder / f"{name}.json"
        if not path.is_file():
            raise FileNotFoundError(name)
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError(name)
        sections.append(report_destination(payload))
    return {"destinations": sections}
