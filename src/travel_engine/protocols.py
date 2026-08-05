"""Routing injection surface for travel_engine — pure types, no I/O."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel


class RouteLeg(BaseModel):
    from_place_id: UUID
    to_place_id: UUID
    duration_min: int
    distance_km: float
    used_fallback: bool = False


class RoutingProvider(Protocol):
    async def travel_matrix(
        self, waypoints: list[tuple[UUID, float, float]]
    ) -> list[RouteLeg]:
        """
        Full directed pairwise legs for all waypoints (i != j).
        Never raises for 'no route' — adapters use geo fallbacks and set used_fallback.
        """
        ...

    async def route_polyline(
        self, waypoints: list[tuple[float, float]]
    ) -> str | None:
        """
        Encoded polyline for a route through waypoints IN ORDER (2+ points).

        Returns None if unavailable (haversine fallback / missing geometry / soft
        failure). Never raises. Used AFTER route order is chosen — not during
        travel_matrix permutation search.
        """
        ...


def legs_to_lookup(legs: list[RouteLeg]) -> dict[tuple[UUID, UUID], RouteLeg]:
    """Index legs by (from_place_id, to_place_id). Last write wins on duplicates."""
    return {(leg.from_place_id, leg.to_place_id): leg for leg in legs}
