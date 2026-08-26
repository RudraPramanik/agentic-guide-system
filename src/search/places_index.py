"""Qdrant upsert / semantic search / ground-truth indexed count for places."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

import structlog
from qdrant_client import models as qmodels
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from src.config import get_settings
from src.places.models import Place
from src.search.client import get_qdrant_client, is_qdrant_available
from src.search.embeddings import embed_batch, embed_text

log = structlog.get_logger()


@dataclass
class PlaceSearchResult:
    place_id: str
    score: float
    name: str | None = None
    destination_id: str | None = None


def _canonical_text(place: Place) -> str:
    """Embed text is derived from ENRICHED output only — enriched_tags, never raw tags."""
    tags_csv = ", ".join(place.enriched_tags or [])
    return f"{place.summary}\n{tags_csv}"


def _payload_for(place: Place, destination_id: uuid.UUID) -> dict:
    return {
        "destination_id": str(destination_id),
        "place_id": str(place.id),
        "name": place.name,
        "osm_id": place.osm_id,
        "category": place.category,
    }


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
)
async def _upsert_points_impl(points: list) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    await asyncio.wait_for(
        client.upsert(collection_name=settings.QDRANT_PLACES_COLLECTION, points=points),
        timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
    )


async def _upsert_points(points: list) -> bool:
    if not points:
        return False
    try:
        await _upsert_points_impl(points)
        return True
    except Exception as e:
        log.warning("qdrant.upsert_failed", error=str(e), count=len(points))
        return False


async def upsert_place(place: Place, destination_id: uuid.UUID) -> bool:
    """
    Single-place upsert — kept for callers needing to re-index one place.
    Deterministic point_id = str(place.id).
    """
    if not place.summary:
        return False
    vector = await embed_text(_canonical_text(place))
    if not vector:
        return False
    point = qmodels.PointStruct(
        id=str(place.id),
        vector=vector,
        payload=_payload_for(place, destination_id),
    )
    return await _upsert_points([point])


async def upsert_places_batch(places: list[Place], destination_id: uuid.UUID) -> int:
    """
    Batches embedding (embed_batch) AND the Qdrant write (one upsert per chunk).
    Returns count of points actually written.
    """
    eligible = [p for p in places if p.summary]
    if not eligible:
        return 0
    texts = [_canonical_text(p) for p in eligible]
    vectors = await embed_batch(texts)
    points = [
        qmodels.PointStruct(
            id=str(place.id),
            vector=vector,
            payload=_payload_for(place, destination_id),
        )
        for place, vector in zip(eligible, vectors)
        if vector
    ]
    if not points:
        return 0
    ok = await _upsert_points(points)
    return len(points) if ok else 0


async def search_places(
    query: str, destination_id: uuid.UUID, top_k: int = 10
) -> list[PlaceSearchResult]:
    if not is_qdrant_available():
        return []
    vector = await embed_text(query)
    if not vector:
        return []
    try:
        settings = get_settings()
        client = get_qdrant_client()
        response = await asyncio.wait_for(
            client.query_points(
                collection_name=settings.QDRANT_PLACES_COLLECTION,
                query=vector,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="destination_id",
                            match=qmodels.MatchValue(value=str(destination_id)),
                        ),
                    ]
                ),
                limit=top_k,
            ),
            timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
        )
    except Exception as e:
        log.warning("qdrant.search_failed", error=str(e))
        return []
    return [
        PlaceSearchResult(
            place_id=r.payload["place_id"],
            score=r.score,
            name=r.payload.get("name"),
            destination_id=r.payload.get("destination_id"),
        )
        for r in response.points
    ]


async def count_indexed(destination_id: uuid.UUID) -> int:
    """
    Ground truth for Destination.indexed_count — Qdrant count filtered by destination_id.
    """
    if not is_qdrant_available():
        return 0
    try:
        settings = get_settings()
        client = get_qdrant_client()
        result = await asyncio.wait_for(
            client.count(
                collection_name=settings.QDRANT_PLACES_COLLECTION,
                count_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="destination_id",
                            match=qmodels.MatchValue(value=str(destination_id)),
                        ),
                    ]
                ),
            ),
            timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
        )
        return result.count
    except Exception as e:
        log.warning("qdrant.count_failed", error=str(e))
        return 0
