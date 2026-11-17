"""Idempotency key is not the preference-cache key."""

from __future__ import annotations

import uuid

from src.planner.cache import build_planner_cache_key
from src.planner.runs.identity import (
    compute_input_hash,
    resolve_idempotency_key,
)
from src.planner.schemas import PlanRequest


def _body(**overrides) -> PlanRequest:
    data = {
        "destination_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "raw_input": "  tea   gardens  ",
        "days": 3,
        "base_lat": 27.0414,
        "base_lng": 88.263,
        "accommodation_label": "Hill stay",
    }
    data.update(overrides)
    return PlanRequest(**data)


def test_same_body_and_session_share_fallback_key() -> None:
    body = _body()
    first, first_hash = resolve_idempotency_key(None, body, 27.0414, 88.263, "sess-a")
    second, second_hash = resolve_idempotency_key("  ", body, 27.0414, 88.263, "sess-a")
    assert first == second
    assert first_hash == second_hash
    assert first_hash == compute_input_hash(body, 27.0414, 88.263)


def test_two_sessions_do_not_share_fallback_key() -> None:
    body = _body()
    guest_a, hash_a = resolve_idempotency_key(None, body, 27.0414, 88.263, "sess-a")
    guest_b, hash_b = resolve_idempotency_key(None, body, 27.0414, 88.263, "sess-b")
    assert guest_a != guest_b
    assert hash_a == hash_b


def test_over_long_header_uses_fallback() -> None:
    body = _body()
    header = "k" * 129
    key, _ = resolve_idempotency_key(header, body, 27.0414, 88.263, "sess-a")
    fallback, _ = resolve_idempotency_key(None, body, 27.0414, 88.263, "sess-a")
    assert key == fallback
    assert key != header


def test_header_wins_and_label_is_ignored() -> None:
    labeled = _body()
    unlabeled = _body(accommodation_label=None)
    key, digest = resolve_idempotency_key("client-key", labeled, 27.0414, 88.263, "sess-a")
    _, other = resolve_idempotency_key(None, unlabeled, 27.0414, 88.263, "sess-a")
    assert key == "client-key"
    assert digest == other


def test_fallback_is_not_the_cache_key() -> None:
    body = _body()
    key, _ = resolve_idempotency_key(None, body, 27.0414, 88.263, "sess-a")
    assert key != build_planner_cache_key(body, 27.0414, 88.263)
