"""OSRM adapter — implements travel_engine RoutingProvider via geo/osrm.

Maps get_route fallback_used onto RouteLeg.used_fallback. Does not touch
LangGraph / TravelState (used_osrm_fallback is P5).
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from src.config import get_settings
from src.geo.osrm import get_route
from src.travel_engine.protocols import RouteLeg


class OsrmRoutingProvider:
    """Adapter: pairwise get_route → list[RouteLeg] (bounded concurrency)."""

    async def travel_matrix(
        self, waypoints: list[tuple[UUID, float, float]]
    ) -> list[RouteLeg]:
        if len(waypoints) < 2:
            return []

        concurrency = max(1, int(get_settings().OSRM_MATRIX_MAX_CONCURRENCY))
        sem = asyncio.Semaphore(concurrency)

        async def _leg(
            from_id: UUID,
            lat_i: float,
            lng_i: float,
            to_id: UUID,
            lat_j: float,
            lng_j: float,
        ) -> RouteLeg:
            async with sem:
                result = await get_route([(lat_i, lng_i), (lat_j, lng_j)])
            return RouteLeg(
                from_place_id=from_id,
                to_place_id=to_id,
                duration_min=round(result.duration_min),
                distance_km=result.distance_km,
                used_fallback=result.fallback_used,
            )

        tasks = [
            _leg(from_id, lat_i, lng_i, to_id, lat_j, lng_j)
            for i, (from_id, lat_i, lng_i) in enumerate(waypoints)
            for j, (to_id, lat_j, lng_j) in enumerate(waypoints)
            if i != j
        ]
        return list(await asyncio.gather(*tasks))

    async def route_polyline(
        self, waypoints: list[tuple[float, float]]
    ) -> str | None:
        """Thin wrapper over geo.osrm.get_route — fail-soft, never raises."""
        try:
            result = await get_route(waypoints)
        except Exception:
            return None
        if result.fallback_used:
            return None
        poly = result.encoded_polyline
        if not poly:
            return None
        return poly
