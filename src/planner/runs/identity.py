"""Idempotency key for one generate submit. Not the preference-cache key."""

from __future__ import annotations

import hashlib

from src.planner.cache import normalize_raw_input
from src.planner.schemas import PlanRequest

_KEY_MAX_LEN = 128


def _sha256(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def request_material(body: PlanRequest, base_lat: float, base_lng: float) -> str:
    """Canonical plan body. Accommodation label is display-only and excluded."""
    normalized = normalize_raw_input(body.raw_input)
    raw_hash = _sha256(normalized)
    days_or_0 = body.days if body.days is not None else 0
    return (
        f"{body.destination_id}:{raw_hash}:{days_or_0}:"
        f"{round(base_lat, 3)}:{round(base_lng, 3)}"
    )


def compute_input_hash(body: PlanRequest, base_lat: float, base_lng: float) -> str:
    return _sha256(request_material(body, base_lat, base_lng))


def compute_fallback_key(
    body: PlanRequest,
    base_lat: float,
    base_lng: float,
    session_id: str,
) -> str:
    material = request_material(body, base_lat, base_lng) + ":" + session_id
    return _sha256(material)


def resolve_idempotency_key(
    header: str | None,
    body: PlanRequest,
    base_lat: float,
    base_lng: float,
    session_id: str,
) -> tuple[str, str]:
    """Return ``(idempotency_key, input_hash)``.

    A header of 1..128 characters is the key. Missing, blank, and longer
    headers use the session digest. The request still proceeds.
    """
    digest = compute_input_hash(body, base_lat, base_lng)
    raw = (header or "").strip()
    if 1 <= len(raw) <= _KEY_MAX_LEN:
        return raw, digest
    return compute_fallback_key(body, base_lat, base_lng, session_id), digest
