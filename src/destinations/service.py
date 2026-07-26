"""Destination service — cache-aside search via DB + Nominatim geocode."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.destinations.exceptions import DestinationNotFoundError
from src.destinations.models import Destination
from src.destinations.readiness import compute_readiness
from src.destinations.repository import DestinationRepository
from src.destinations.schemas import DestinationReadinessOut
from src.geo.geocoder import geocode


class DestinationService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DestinationRepository(session)

    async def search(self, query: str) -> list[Destination]:
        """Cache-aside: DB ILIKE hit → return; miss → geocode → atomic upsert → commit."""
        results = await self.repo.search_by_name(query)
        if results:
            return results

        geocoded = await geocode(query)
        if geocoded is None:
            raise DestinationNotFoundError(query=query)

        dest = await self.repo.upsert_from_geocoded(geocoded)
        await self.session.commit()
        await self.session.refresh(dest)
        return [dest]

    async def get_by_id(self, destination_id: uuid.UUID) -> Destination:
        dest = await self.repo.get_by_id(destination_id)
        if dest is None:
            raise DestinationNotFoundError(destination_id=str(destination_id))
        return dest

    async def get_readiness(self, destination_id: uuid.UUID) -> DestinationReadinessOut:
        """Compute readiness from denormalized counters. P2: search_available=False."""
        dest = await self.get_by_id(destination_id)
        search_available = False  # P2: Qdrant wired in P3
        result = compute_readiness(
            dest.place_count,
            dest.enriched_count,
            dest.indexed_count,
            search_available,
        )
        return DestinationReadinessOut(
            destination_id=dest.id,
            score=result.score,
            tier=result.tier,
            place_count=result.place_count,
            enriched_pct=result.enriched_pct,
            indexed_pct=result.indexed_pct,
            message=result.message,
        )
