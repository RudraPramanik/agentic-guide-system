"""Unit tests for travel_engine.candidate_normalizer (v8.3 slice 4.1)."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

from src.travel_engine.candidate_normalizer import (
    normalize_candidates,
    normalize_category,
    normalize_name_key,
)
from src.travel_engine.place_selector import PlaceCandidate

_NORMALIZER = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "travel_engine"
    / "candidate_normalizer.py"
)


def _cand(
    name: str,
    category: str = "monastery",
    *,
    lat: float = 27.0,
    lng: float = 88.0,
    place_id=None,
    user_selected: bool = False,
    aliases: list[str] | None = None,
    parent_place_id=None,
    evidence_count: int = 0,
) -> PlaceCandidate:
    return PlaceCandidate(
        id=place_id or uuid4(),
        name=name,
        category=category,
        enriched_tags=[],
        lat=lat,
        lng=lng,
        user_selected=user_selected,
        aliases=aliases or [],
        parent_place_id=parent_place_id,
        evidence_count=evidence_count,
    )


def test_name_variants_share_comparison_key() -> None:
    assert normalize_name_key("Ghoom Monastery!") == normalize_name_key(
        "  ghoom   monastery  "
    )


def test_monastery_name_variants_collapse() -> None:
    a = _cand("Ghoom Monastery", lat=27.3300, lng=88.1300)
    b = _cand("ghoom monastery", lat=27.3301, lng=88.1301)
    out = normalize_candidates([a, b])
    assert len(out) == 1


def test_monastery_alias_pair_collapses() -> None:
    a = _cand("Ghoom Monastery", lat=27.3300, lng=88.1300)
    b = _cand("Ghum Monastery", lat=27.33005, lng=88.13005)
    out = normalize_candidates([a, b])
    assert len(out) == 1


def test_adjacent_distinct_attractions_stay() -> None:
    a = _cand("Tiger Hill", "viewpoint", lat=27.041, lng=88.266)
    b = _cand("Batasia Loop", "attraction", lat=27.0415, lng=88.2665)
    out = normalize_candidates([a, b])
    assert {c.name for c in out} == {"Tiger Hill", "Batasia Loop"}


def test_exact_id_collapse() -> None:
    shared = uuid4()
    a = _cand("Same", place_id=shared, lat=27.0, lng=88.0)
    b = _cand("Same Copy", place_id=shared, lat=27.1, lng=88.1)
    out = normalize_candidates([a, b])
    assert len(out) == 1
    assert out[0].id == shared


def test_category_synonym_maps_and_unknown_stays() -> None:
    assert normalize_category("View Point") == "viewpoint"
    assert normalize_category("trailhead") == "trailhead"


def test_parent_child_collapses() -> None:
    parent = _cand("Ghoom Monastery", lat=27.33, lng=88.13)
    child = _cand(
        "Ghoom Monastery Gate",
        lat=27.40,
        lng=88.20,
        parent_place_id=parent.id,
    )
    out = normalize_candidates([child, parent])
    assert len(out) == 1
    assert out[0].id == parent.id


def test_user_selected_retained() -> None:
    kept = _cand(
        "Ghoom Monastery",
        lat=27.3300,
        lng=88.1300,
        user_selected=True,
        evidence_count=0,
    )
    rival = _cand(
        "ghoom monastery",
        lat=27.3301,
        lng=88.1301,
        user_selected=False,
        evidence_count=5,
    )
    out = normalize_candidates([rival, kept])
    assert len(out) == 1
    assert out[0].id == kept.id
    assert out[0].user_selected is True


def test_idempotent_second_pass() -> None:
    a = _cand("Ghoom Monastery", lat=27.3300, lng=88.1300)
    b = _cand("ghoom monastery", lat=27.3301, lng=88.1301)
    c = _cand("Tiger Hill", "viewpoint", lat=27.04, lng=88.26)
    first = normalize_candidates([a, b, c])
    second = normalize_candidates(first)
    assert {x.id for x in first} == {x.id for x in second}


def test_missing_optional_fields_do_not_invent_data() -> None:
    bare = PlaceCandidate(
        id=uuid4(),
        name="Plain Spot",
        category="attraction",
        enriched_tags=[],
        lat=27.0,
        lng=88.0,
    )
    out = normalize_candidates([bare])
    assert len(out) == 1
    assert out[0].aliases == []
    assert out[0].parent_place_id is None
    assert out[0].evidence_count == 0
    assert out[0].source is None
    assert out[0].user_selected is False


def test_normalizer_has_no_forbidden_imports() -> None:
    tree = ast.parse(_NORMALIZER.read_text(encoding="utf-8-sig"))
    forbidden = {
        "src.geo",
        "httpx",
        "sqlalchemy",
        "litellm",
        "qdrant_client",
        "redis",
        "requests",
        "aiohttp",
    }
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.add(node.module.split(".")[0])
    assert not (found & forbidden)
    text = _NORMALIZER.read_text(encoding="utf-8-sig")
    assert "get_settings" not in text
    assert "TRAVEL_ENGINE_V2_ENABLED" not in text
