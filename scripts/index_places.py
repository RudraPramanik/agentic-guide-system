"""
Index enriched places into Qdrant for semantic search.
Usage: python scripts/index_places.py --destination "Darjeeling" --batch-size 10 --limit 0
Idempotent (point_id = str(place.id)). Commits destination.indexed_count on success.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import AsyncSessionLocal, dispose_engine
from src.core.observability.logging import configure_logging, get_logger
from src.destinations.repository import DestinationRepository
from src.places.models import Place
from src.search.client import ensure_places_collection, is_qdrant_available
from src.search.embeddings import ensure_embedding_model_loaded, is_embeddings_available
from src.search.places_index import count_indexed, upsert_places_batch

log = get_logger(__name__)


async def index_places(
    session: AsyncSession,
    destination_id: uuid.UUID,
    batch_size: int,
    limit: int,
) -> int:
    """Does NOT open session and does NOT commit."""
    stmt = select(Place).where(
        Place.destination_id == destination_id,
        Place.summary.is_not(None),
        Place.deleted_at.is_(None),
    )
    if limit and limit > 0:  # LOCKED (v2): NEVER call .limit(0)
        stmt = stmt.limit(limit)
    places = list((await session.execute(stmt)).scalars().all())

    total_success = 0
    for i in range(0, len(places), batch_size):
        chunk = places[i : i + batch_size]
        total_success += await upsert_places_batch(chunk, destination_id)

    indexed_total = await count_indexed(destination_id)
    await DestinationRepository(session).update(
        destination_id, {"indexed_count": indexed_total}
    )
    return total_success


async def _resolve_destination_id(
    session: AsyncSession, destination_name: str
) -> uuid.UUID | None:
    dest_repo = DestinationRepository(session)
    matches = await dest_repo.search_by_name(destination_name)
    if not matches:
        return None
    for dest in matches:
        if dest.name.lower() == destination_name.lower():
            return dest.id
    return matches[0].id


async def run_index(
    destination_name: str, batch_size: int, limit: int
) -> int:
    await ensure_places_collection()
    await ensure_embedding_model_loaded()

    if not is_qdrant_available() or not is_embeddings_available():
        print(
            "WARNING: Qdrant and/or embeddings unavailable — "
            "indexing will degrade (indexed_count may be 0). Exiting 0."
        )

    async with AsyncSessionLocal() as session:
        destination_id = await _resolve_destination_id(session, destination_name)
        if destination_id is None:
            print(
                f"Destination {destination_name!r} not found — seed/enrich first.",
                file=sys.stderr,
            )
            return 1

        stmt = select(func.count()).select_from(Place).where(
            Place.destination_id == destination_id,
            Place.summary.is_not(None),
            Place.deleted_at.is_(None),
        )
        if limit and limit > 0:
            total = min(limit, int(await session.scalar(stmt) or 0))
        else:
            total = int(await session.scalar(stmt) or 0)

        success = await index_places(session, destination_id, batch_size, limit)
        indexed_total = await count_indexed(destination_id)
        await session.commit()
        print(
            f"Indexed {success}/{total} places for {destination_name} "
            f"(Qdrant ground truth: {indexed_total})"
        )
    return 0


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Index enriched places into Qdrant")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--limit", type=int, default=0, help="0 = unlimited")
    args = parser.parse_args()
    try:
        code = asyncio.run(run_index(args.destination, args.batch_size, args.limit))
    finally:
        asyncio.run(dispose_engine())
    raise SystemExit(code)


if __name__ == "__main__":
    main()
