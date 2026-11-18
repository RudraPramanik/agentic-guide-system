"""Readiness V2 pure-function proofs."""

from __future__ import annotations

from datetime import datetime, timezone

from src.destinations.readiness import (
    READINESS_CLUSTER_KM,
    READINESS_PROXIMITY_M,
    ReadinessPlace,
    compute_readiness_v2,
)
from src.travel_engine.travel_rules import CLUSTER_RADIUS_KM, NORMALIZER_PROXIMITY_M


def _place(
    index: int,
    *,
    name: str | None = None,
    category: str = "monastery",
    lat: float = 27.0,
    lng: float = 88.0,
    source: str | None = "osm",
    retrieved_at: datetime | None = None,
) -> ReadinessPlace:
    return ReadinessPlace(
        id=f"{index:04d}",
        name=name or f"Place {index}",
        category=category,
        lat=lat,
        lng=lng,
        source=source,
        retrieved_at=retrieved_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _spread(count: int, lat: float, categories: tuple[str, ...]) -> list[ReadinessPlace]:
    return [
        _place(
            index,
            category=categories[index % len(categories)],
            lat=lat,
            lng=88.0 + (index % 5) * 0.001,
        )
        for index in range(count)
    ]


def test_constants_match_engine_distances() -> None:
    assert READINESS_PROXIMITY_M == NORMALIZER_PROXIMITY_M
    assert READINESS_CLUSTER_KM == CLUSTER_RADIUS_KM


def test_ten_clustered_places_are_limited_for_three_days() -> None:
    places = _spread(10, 27.0, ("monastery", "viewpoint", "museum"))
    result = compute_readiness_v2(places, 3)
    assert result.tier == "limited"
    assert 0.3 <= result.score < 0.7
    assert result.message is not None
    assert "need 12" in result.message or "1 cluster" in result.message


def test_twelve_spread_places_are_ready_for_three_days() -> None:
    places = _spread(6, 27.0, ("monastery", "viewpoint", "museum"))
    places.extend(
        _spread(6, 27.12, ("monastery", "viewpoint", "museum"))
    )
    # Second cluster ids must not collide with the first six.
    places = places[:6] + [
        _place(
            100 + index,
            category=("monastery", "viewpoint", "museum")[index % 3],
            lat=27.12,
            lng=88.0 + index * 0.001,
        )
        for index in range(6)
    ]
    result = compute_readiness_v2(places, 3)
    assert result.tier == "ready"
    assert result.score >= 0.7
    assert result.message is None


def test_nine_places_are_sparse() -> None:
    result = compute_readiness_v2(_spread(9, 27.0, ("monastery", "viewpoint", "museum")), 1)
    assert result.tier == "sparse"
    assert result.score < 0.3


def test_null_island_blocks_ready() -> None:
    places = _spread(10, 27.0, ("monastery", "viewpoint", "museum"))
    places.append(_place(99, lat=0.0, lng=0.0, category="park"))
    result = compute_readiness_v2(places, 1)
    assert result.tier != "ready"
    assert result.place_count == 10


def test_same_name_within_100_meters_counts_once() -> None:
    places = [
        _place(1, name="Same Spot", lat=27.0, lng=88.0),
        _place(2, name="same spot", lat=27.0009, lng=88.0),
    ]
    result = compute_readiness_v2(places, 1)
    assert result.place_count == 1


def test_seventy_percent_cluster_passes_and_larger_share_fails() -> None:
    categories = ("monastery", "viewpoint", "museum")
    passing = [
        _place(index, category=categories[index % 3], lat=27.0, lng=88.0 + (index % 4) * 0.001)
        for index in range(14)
    ]
    passing.extend(
        _place(100 + index, category=categories[index % 3], lat=27.2, lng=88.2)
        for index in range(6)
    )
    ok = compute_readiness_v2(passing, 3)
    assert ok.tier == "ready"

    failing = [
        _place(index, category=categories[index % 3], lat=27.0, lng=88.0)
        for index in range(15)
    ]
    failing.extend(
        _place(100 + index, category=categories[index % 3], lat=27.2, lng=88.2)
        for index in range(5)
    )
    bad = compute_readiness_v2(failing, 3)
    assert bad.tier == "limited"
    assert bad.message is not None
    assert "cluster" in bad.message


def test_evidence_share_does_not_change_a_ready_message() -> None:
    places = _spread(10, 27.0, ("monastery", "viewpoint", "museum"))
    places[0] = _place(0, category="monastery", source=None, retrieved_at=None)
    result = compute_readiness_v2(places, 1)
    assert result.tier == "ready"
    assert result.message is None
