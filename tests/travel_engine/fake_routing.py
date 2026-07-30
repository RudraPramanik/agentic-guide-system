"""Deterministic FakeRoutingProvider for travel_engine tests (no network)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from src.travel_engine.protocols import RouteLeg


class FakeRoutingProvider:
    """
    Implements RoutingProvider.travel_matrix with a full directed pairwise set.

    duration_for(from_id, to_id) -> (duration_min, distance_km).
    Default: constant 30 min / 1.0 km for every ordered pair.
    """

    def __init__(
        self,
        duration_for: Callable[[UUID, UUID], tuple[int, float]] | None = None,
        *,
        default_duration_min: int = 30,
        default_distance_km: float = 1.0,
    ) -> None:
        self._duration_for = duration_for
        self._default_duration_min = default_duration_min
        self._default_distance_km = default_distance_km
        self.call_count = 0

    async def travel_matrix(
        self, waypoints: list[tuple[UUID, float, float]]
    ) -> list[RouteLeg]:
        self.call_count += 1
        ids = [w[0] for w in waypoints]
        legs: list[RouteLeg] = []
        for a in ids:
            for b in ids:
                if a == b:
                    continue
                if self._duration_for is not None:
                    dur, dist = self._duration_for(a, b)
                else:
                    dur, dist = self._default_duration_min, self._default_distance_km
                legs.append(
                    RouteLeg(
                        from_place_id=a,
                        to_place_id=b,
                        duration_min=dur,
                        distance_km=dist,
                    )
                )
        return legs
