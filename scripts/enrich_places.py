"""
Enrich destination places with LLM summaries + controlled tags.
Usage: python scripts/enrich_places.py --destination "Darjeeling" --batch-size 10 --limit 0
Re-runnable (skips places that already have summary). Commits on success.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.database.session import AsyncSessionLocal, dispose_engine
from src.core.observability.logging import configure_logging, get_logger
from src.destinations.repository import DestinationRepository
from src.places.models import Place
from src.places.service import PlaceService

log = get_logger(__name__)


async def enrich_places(
    session: AsyncSession,
    destination_id: uuid.UUID,
    batch_size: int,
    limit: int,
) -> int:
    """Does NOT open session and does NOT commit — caller (CLI wrapper) owns commit."""
    settings = get_settings()
    stmt = select(Place).where(
        Place.destination_id == destination_id,
        Place.summary.is_(None),
        Place.deleted_at.is_(None),
    )
    if limit and limit > 0:  # LOCKED (v2): NEVER call .limit(0)
        stmt = stmt.limit(limit)
    places = list((await session.execute(stmt)).scalars().all())

    service = PlaceService(session)
    semaphore = asyncio.Semaphore(settings.ENRICH_BATCH_LLM_CONCURRENCY)
    success = 0

    for i in range(0, len(places), batch_size):
        chunk = places[i : i + batch_size]

        async def _parse_one(place: Place):
            async with semaphore:
                return place, await service._call_llm_and_parse(place)

        results = await asyncio.gather(*[_parse_one(p) for p in chunk])

        for place, parsed in results:
            if parsed is None:
                continue
            try:
                async with session.begin_nested():
                    await service.repo.update(
                        place.id,
                        {
                            "summary": parsed.summary,
                            "enriched_tags": parsed.tags,
                        },
                    )
                success += 1
            except Exception as e:  # noqa: BLE001 — one bad write must not abort the batch
                log.warning("enrich.persist_failed", place_id=str(place.id), error=str(e))
                continue

        if (i + batch_size) % 50 == 0 or (i + batch_size) >= len(places):
            print(f"  ... {min(i + batch_size, len(places))}/{len(places)} processed")

    enriched_total = await session.scalar(
        select(func.count())
        .select_from(Place)
        .where(
            Place.destination_id == destination_id,
            Place.summary.is_not(None),
            Place.deleted_at.is_(None),
        )
    )
    await DestinationRepository(session).update(
        destination_id, {"enriched_count": int(enriched_total or 0)}
    )
    return success


async def _resolve_destination_id(
    session: AsyncSession, destination_name: str
) -> uuid.UUID | None:
    dest_repo = DestinationRepository(session)
    matches = await dest_repo.search_by_name(destination_name)
    if not matches:
        return None
    # Prefer exact case-insensitive name match when available
    for dest in matches:
        if dest.name.lower() == destination_name.lower():
            return dest.id
    return matches[0].id


async def run_enrich(
    destination_name: str, batch_size: int, limit: int
) -> int:
    async with AsyncSessionLocal() as session:
        destination_id = await _resolve_destination_id(session, destination_name)
        if destination_id is None:
            print(
                f"Destination {destination_name!r} not found — seed it first.",
                file=sys.stderr,
            )
            return 1

        stmt = select(func.count()).select_from(Place).where(
            Place.destination_id == destination_id,
            Place.summary.is_(None),
            Place.deleted_at.is_(None),
        )
        if limit and limit > 0:
            total = min(limit, int(await session.scalar(stmt) or 0))
        else:
            total = int(await session.scalar(stmt) or 0)

        success = await enrich_places(session, destination_id, batch_size, limit)
        await session.commit()
        print(
            f"Enriched {success}/{total} places for {destination_name}"
        )
    return 0


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Enrich places with LLM summaries/tags")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int, default=0, help="0 = unlimited")
    args = parser.parse_args()
    try:
        code = asyncio.run(run_enrich(args.destination, args.batch_size, args.limit))
    finally:
        asyncio.run(dispose_engine())
    raise SystemExit(code)


if __name__ == "__main__":
    main()
