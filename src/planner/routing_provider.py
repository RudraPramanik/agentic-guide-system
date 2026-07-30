"""OSRM adapter — implements travel_engine RoutingProvider via geo/osrm.

Maps get_route fallback_used onto RouteLeg.used_fallback. Does not touch
LangGraph / TravelState (used_osrm_fallback is P5).
"""

from __future__ import annotations

from uuid import UUID

from src.geo.osrm import get_route
from src.travel_engine.protocols import RouteLeg


class OsrmRoutingProvider:
    """Adapter: pairwise get_route → list[RouteLeg]."""

    async def travel_matrix(
        self, waypoints: list[tuple[UUID, float, float]]
    ) -> list[RouteLeg]:
        if len(waypoints) < 2:
            return []

        legs: list[RouteLeg] = []
        for i, (from_id, lat_i, lng_i) in enumerate(waypoints):
            for j, (to_id, lat_j, lng_j) in enumerate(waypoints):
                if i == j:
                    continue
                result = await get_route([(lat_i, lng_i), (lat_j, lng_j)])
                legs.append(
                    RouteLeg(
                        from_place_id=from_id,
                        to_place_id=to_id,
                        duration_min=round(result.duration_min),
                        distance_km=result.distance_km,
                        used_fallback=result.fallback_used,
                    )
                )
        return legs
