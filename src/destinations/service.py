"""Destination service — cache-aside search via DB + Nominatim geocode."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.cache.backends import get_cache_backend
from src.core.database.session import AsyncSessionLocal
from src.core.exceptions import ExternalServiceError
from src.core.observability.logging import get_logger
from src.destinations.exceptions import DestinationNotFoundError
from src.destinations.ingest import ingest_destination_pois
from src.destinations.models import Destination
from src.destinations.readiness import compute_readiness
from src.destinations.repository import DestinationRepository
from src.destinations.schemas import DestinationPrepareOut, DestinationReadinessOut
from src.geo.geocoder import geocode
from src.search.client import is_qdrant_available

log = get_logger(__name__)


def _prepare_lock_key(destination_id: uuid.UUID) -> str:
    return f"dest-prepare:{destination_id}"


async def _run_prepare_ingest(destination_id: uuid.UUID, radius_km: float) -> None:
    """Own session — must not use the HTTP request session after the response."""
    cache = get_cache_backend()
    lock_key = _prepare_lock_key(destination_id)
    try:
        async with AsyncSessionLocal() as session:
            dest = await DestinationRepository(session).get_by_id(destination_id)
            if dest is None:
                return
            await ingest_destination_pois(session, dest, radius_km)
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — background must not crash the worker
        log.warning(
            "destinations.prepare_failed",
            destination_id=str(destination_id),
            error=str(exc),
        )
    finally:
        await cache.delete(lock_key)


class DestinationService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DestinationRepository(session)

    async def search(self, query: str) -> list[Destination]:
        """Cache-aside: DB ILIKE hit → return; miss → geocode → atomic upsert → commit."""
        results = await self.repo.search_by_name(query)
        if results:
            return results

        try:
            geocoded = await asyncio.wait_for(
                geocode(query),
                timeout=get_settings().SEARCH_GEOCODE_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            geocoded = None
        except ExternalServiceError:
            # Nominatim policy/rate block → 502; do not map to not_found.
            raise
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
        """Compute readiness from denormalized counters + live Qdrant availability."""
        dest = await self.get_by_id(destination_id)
        search_available = is_qdrant_available()
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

    async def prepare(
        self,
        destination_id: uuid.UUID,
        radius_km: float | None = None,
    ) -> DestinationPrepareOut:
        """Kick off Overpass ingest, or no-op if already at the planner place floor."""
        settings = get_settings()
        dest = await self.get_by_id(destination_id)
        resolved_radius = (
            float(radius_km)
            if radius_km is not None
            else settings.DESTINATIONS_PREPARE_DEFAULT_RADIUS_KM
        )
        cap = settings.DESTINATIONS_PREPARE_MAX_RADIUS_KM
        if resolved_radius > cap:
            resolved_radius = cap

        if dest.place_count >= settings.PLANNER_ABSOLUTE_MIN_PLACES:
            return DestinationPrepareOut(
                destination_id=dest.id,
                status="ready",
                place_count=dest.place_count,
            )

        cache = get_cache_backend()
        lock_key = _prepare_lock_key(dest.id)
        if await cache.get(lock_key):
            return DestinationPrepareOut(
                destination_id=dest.id,
                status="preparing",
                place_count=dest.place_count,
            )

        await cache.set(
            lock_key,
            "1",
            ttl_seconds=settings.DESTINATIONS_PREPARE_LOCK_TTL_SECONDS,
        )
        asyncio.create_task(_run_prepare_ingest(dest.id, resolved_radius))
        return DestinationPrepareOut(
            destination_id=dest.id,
            status="preparing",
            place_count=dest.place_count,
        )
