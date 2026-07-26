"""Pure readiness scoring unit tests — no I/O."""

from __future__ import annotations

from src.destinations.readiness import compute_readiness


def test_compute_readiness_sparse() -> None:
    result = compute_readiness(0, 0, 0, False)

    assert result.tier == "sparse"
    assert result.score < 0.3
    assert result.message == "Very limited POI data - results may be generic"
    assert result.enriched_pct == 0.0
    assert result.indexed_pct == 0.0


def test_compute_readiness_place_count_50_is_sparse() -> None:
    result = compute_readiness(50, 0, 0, False)

    assert result.tier == "sparse"
    assert result.score == 0.2
    assert result.message == "Very limited POI data - results may be generic"


def test_compute_readiness_limited() -> None:
    result = compute_readiness(144, 0, 0, False)

    assert result.tier == "limited"
    assert 0.35 <= result.score <= 0.45
    assert result.enriched_pct == 0.0
    assert result.indexed_pct == 0.0
    assert result.message == "Limited enrichment - semantic search not yet available"


def test_compute_readiness_ready() -> None:
    result = compute_readiness(144, 100, 100, True)

    assert result.tier == "ready"
    assert result.score >= 0.7
    assert result.message is None
    assert abs(result.enriched_pct - (100 / 144)) < 1e-9
    assert abs(result.indexed_pct - (100 / 144)) < 1e-9
