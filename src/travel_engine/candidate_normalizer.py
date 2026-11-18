"""Candidate normalization and confidence-based dedup (pure, no I/O).

Collapse rules (first decisive match; no aggressive nearby-name merges):
1. Exact place id
2. Same normalized name within NORMALIZER_PROXIMITY_M
3. Alias hit (candidate.aliases or NORMALIZER_ALIAS_PAIRS)
4. Parent/child when parent_place_id points at another candidate and
   confidence ≥ NORMALIZER_MERGE_CONFIDENCE

User-selected candidates are retained. Two user-selected near-duplicates
both survive unless they share an exact id. Survivors keep original lat/lng.
"""

from __future__ import annotations

import math
import re
from uuid import UUID

from src.travel_engine.place_selector import PlaceCandidate
from src.travel_engine.travel_rules import (
    CATEGORY_SYNONYMS,
    NORMALIZER_ALIAS_PAIRS,
    NORMALIZER_CONF_ALIAS,
    NORMALIZER_CONF_EXACT_ID,
    NORMALIZER_CONF_NAME_PROXIMITY,
    NORMALIZER_CONF_PARENT_CHILD,
    NORMALIZER_MERGE_CONFIDENCE,
    NORMALIZER_PROXIMITY_M,
)


def normalize_name_key(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace — comparison only."""
    lowered = name.lower().strip()
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    return " ".join(cleaned.split())


def normalize_category(category: str) -> str:
    """Map known synonyms onto structural vocabulary; unknown stays as-is."""
    key = normalize_name_key(category)
    return CATEGORY_SYNONYMS.get(key, category)


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in meters (pure math; not a geo gateway)."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _alias_keys(place: PlaceCandidate) -> set[str]:
    keys = {normalize_name_key(place.name)}
    for alias in place.aliases:
        keys.add(normalize_name_key(alias))
    return keys


def _static_aliases(name_key: str) -> set[str]:
    related = {name_key}
    for left, right in NORMALIZER_ALIAS_PAIRS:
        if name_key in (left, right):
            related.add(left)
            related.add(right)
    return related


def _names_alias_linked(a: PlaceCandidate, b: PlaceCandidate) -> bool:
    a_keys = _alias_keys(a) | _static_aliases(normalize_name_key(a.name))
    b_keys = _alias_keys(b) | _static_aliases(normalize_name_key(b.name))
    return bool(a_keys & b_keys)


def _within_proximity(a: PlaceCandidate, b: PlaceCandidate) -> bool:
    return _haversine_m(a.lat, a.lng, b.lat, b.lng) <= NORMALIZER_PROXIMITY_M


def _prefer(a: PlaceCandidate, b: PlaceCandidate) -> PlaceCandidate:
    """Deterministic survivor when collapsing a pair."""
    if a.user_selected != b.user_selected:
        return a if a.user_selected else b
    if a.evidence_count != b.evidence_count:
        return a if a.evidence_count > b.evidence_count else b
    if a.name != b.name:
        return a if a.name < b.name else b
    return a if str(a.id) <= str(b.id) else b


def _merge_confidence(a: PlaceCandidate, b: PlaceCandidate) -> float | None:
    """Return confidence if a and b should collapse; else None."""
    if a.id == b.id:
        return NORMALIZER_CONF_EXACT_ID

    same_name = normalize_name_key(a.name) == normalize_name_key(b.name)
    if same_name and _within_proximity(a, b):
        return NORMALIZER_CONF_NAME_PROXIMITY

    if _names_alias_linked(a, b) and _within_proximity(a, b):
        return NORMALIZER_CONF_ALIAS

    parent_child = a.parent_place_id == b.id or b.parent_place_id == a.id
    if parent_child and NORMALIZER_CONF_PARENT_CHILD >= NORMALIZER_MERGE_CONFIDENCE:
        return NORMALIZER_CONF_PARENT_CHILD

    return None


def _should_keep_both(a: PlaceCandidate, b: PlaceCandidate) -> bool:
    """Two user-selected near-duplicates both survive unless exact id."""
    return a.id != b.id and a.user_selected and b.user_selected


def normalize_candidates(
    candidates: list[PlaceCandidate],
) -> list[PlaceCandidate]:
    """Deduplicate candidates; survivors keep original display coords/names.

    Idempotent on the survivor id set. Missing optional fields stay absent.
    Category synonyms are used for comparison only and do not rewrite display
    category on the survivor unless callers already passed the canonical value.
    """
    if not candidates:
        return []

    ordered = sorted(
        candidates,
        key=lambda c: (
            not c.user_selected,
            -c.evidence_count,
            c.name,
            str(c.id),
        ),
    )

    survivors: list[PlaceCandidate] = []
    for cand in ordered:
        merged = False
        for idx, kept in enumerate(survivors):
            conf = _merge_confidence(cand, kept)
            if conf is None:
                continue
            if cand.id != kept.id and conf < NORMALIZER_MERGE_CONFIDENCE:
                continue
            if _should_keep_both(cand, kept):
                continue
            survivors[idx] = _prefer(cand, kept)
            merged = True
            break
        if not merged:
            if any(s.id == cand.id for s in survivors):
                continue
            survivors.append(cand)

    survivors.sort(key=lambda c: (c.name, str(c.id)))
    return survivors


def survivor_ids(candidates: list[PlaceCandidate]) -> set[UUID]:
    return {c.id for c in normalize_candidates(candidates)}
