"""Pure destination readiness scoring — no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PLACE_TARGET = 100

_SPARSE_MESSAGE = "Very limited POI data - results may be generic"
_LIMITED_MESSAGE = "Limited enrichment - semantic search not yet available"


@dataclass(frozen=True)
class ReadinessResult:
    score: float
    tier: Literal["ready", "limited", "sparse"]
    place_count: int
    enriched_pct: float
    indexed_pct: float
    message: str | None


def compute_readiness(
    place_count: int,
    enriched_count: int,
    indexed_count: int,
    search_available: bool,
) -> ReadinessResult:
    """
    Pure function — no I/O. Locked P2 formula from docs/steps/step2.md.
    Messages:
      sparse: "Very limited POI data - results may be generic"
      limited: "Limited enrichment - semantic search not yet available" (when enriched_pct < 0.5)
      ready: None
    """
    place_score = min(place_count / PLACE_TARGET, 1.0)
    enriched_pct = enriched_count / place_count if place_count > 0 else 0.0
    indexed_pct = (
        (indexed_count / place_count) if (place_count > 0 and search_available) else 0.0
    )

    score = round(0.4 * place_score + 0.35 * enriched_pct + 0.25 * indexed_pct, 3)
    tier: Literal["ready", "limited", "sparse"]
    if score >= 0.7:
        tier = "ready"
    elif score >= 0.3:
        tier = "limited"
    else:
        tier = "sparse"

    if tier == "sparse":
        message: str | None = _SPARSE_MESSAGE
    elif tier == "limited" and enriched_pct < 0.5:
        message = _LIMITED_MESSAGE
    else:
        message = None

    return ReadinessResult(
        score=score,
        tier=tier,
        place_count=place_count,
        enriched_pct=enriched_pct,
        indexed_pct=indexed_pct,
        message=message,
    )
