"""Qdrant upsert / semantic search / ground-truth indexed count for places."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from qdrant_client import models as qmodels
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from src.config import get_settings
from src.places.models import Place
from src.search.client import (
    collection_uses_hybrid_schema,
    get_qdrant_client,
    is_qdrant_available,
    places_collection,
)
from src.search.embeddings import embed_batch, embed_text
from src.search.sparse import encode_sparse, encode_sparse_batch, is_sparse_available

log = structlog.get_logger()


@dataclass
class PlaceSearchResult:
    place_id: str
    score: float
    name: str | None = None
    destination_id: str | None = None


@dataclass
class PlaceSearchOutcome:
    """Primary hits plus optional fusion diagnostics sidecar (V6.1)."""

    hits: list[PlaceSearchResult] = field(default_factory=list)
    diagnostics: dict[str, Any] | None = None


def _canonical_text(place: Place) -> str:
    """
    Embed/sparse text from enrichment + identity tokens.
    Never uses raw OSM tags — only summary, enriched_tags, name, category.
    """
    parts: list[str] = []
    if place.name:
        parts.append(str(place.name).strip())
    if place.category:
        parts.append(str(place.category).strip())
    if place.summary:
        parts.append(str(place.summary).strip())
    tags_csv = ", ".join(place.enriched_tags or [])
    if tags_csv:
        parts.append(tags_csv)
    return "\n".join(p for p in parts if p)


def _payload_for(place: Place, destination_id: uuid.UUID) -> dict:
    return {
        "destination_id": str(destination_id),
        "place_id": str(place.id),
        "name": place.name,
        "osm_id": place.osm_id,
        "category": place.category,
    }


def _point_vector(dense: list[float], sparse: qmodels.SparseVector | None) -> dict | list[float]:
    """Build Qdrant point vector for hybrid (named) or legacy (unnamed) collections."""
    if not collection_uses_hybrid_schema():
        return dense
    named: dict = {"dense": dense}
    if sparse is not None and sparse.indices:
        named["bm25"] = sparse
    return named


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
)
async def _upsert_points_impl(points: list) -> None:
    settings = get_settings()
    client = get_qdrant_client()
    await asyncio.wait_for(
        client.upsert(collection_name=places_collection(), points=points),
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
    text = _canonical_text(place)
    vector = await embed_text(text)
    if not vector:
        return False
    sparse = encode_sparse(text) if collection_uses_hybrid_schema() else None
    point = qmodels.PointStruct(
        id=str(place.id),
        vector=_point_vector(vector, sparse),
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
    sparse_vecs: list[qmodels.SparseVector | None]
    if collection_uses_hybrid_schema():
        sparse_vecs = list(await encode_sparse_batch(texts))
    else:
        sparse_vecs = [None] * len(eligible)
    points = [
        qmodels.PointStruct(
            id=str(place.id),
            vector=_point_vector(vector, sparse),
            payload=_payload_for(place, destination_id),
        )
        for place, vector, sparse in zip(eligible, vectors, sparse_vecs)
        if vector
    ]
    if not points:
        return 0
    ok = await _upsert_points(points)
    return len(points) if ok else 0


def _destination_filter(destination_id: uuid.UUID) -> qmodels.Filter:
    return qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="destination_id",
                match=qmodels.MatchValue(value=str(destination_id)),
            ),
        ]
    )


def _hits_from_points(points: list) -> list[PlaceSearchResult]:
    hits: list[PlaceSearchResult] = []
    for r in points:
        payload = r.payload or {}
        place_id = payload.get("place_id")
        if not place_id:
            continue
        hits.append(
            PlaceSearchResult(
                place_id=str(place_id),
                score=float(r.score) if r.score is not None else 0.0,
                name=payload.get("name"),
                destination_id=payload.get("destination_id"),
            )
        )
    return hits


def _place_ids(hits: list[PlaceSearchResult]) -> list[str]:
    return [h.place_id for h in hits]


def _base_diagnostics(
    *,
    mode: str,
    collection: str,
    sparse_enabled: bool,
    top_k: int,
    fused_place_ids: list[str] | None = None,
    dense_place_ids: list[str] | None = None,
    sparse_place_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "collection": collection,
        "sparse_enabled": sparse_enabled,
        "fused_place_ids": list(fused_place_ids or []),
        "dense_place_ids": list(dense_place_ids or []),
        "sparse_place_ids": list(sparse_place_ids or []),
        "top_k": top_k,
    }


async def _query_place_ids_fail_soft(
    *,
    client: Any,
    collection: str,
    timeout: float,
    query: Any,
    using: str | None,
    dest_filter: qmodels.Filter,
    limit: int,
) -> list[str]:
    """Single diagnostic subquery — never raises into the search path."""
    try:
        kwargs: dict[str, Any] = {
            "collection_name": collection,
            "query": query,
            "query_filter": dest_filter,
            "limit": limit,
        }
        if using is not None:
            kwargs["using"] = using
        response = await asyncio.wait_for(
            client.query_points(**kwargs),
            timeout=timeout,
        )
        return _place_ids(_hits_from_points(list(response.points or [])))
    except Exception as e:  # noqa: BLE001 — diagnostics fail-soft
        log.debug("qdrant.fusion_diagnostics_subquery_failed", error=str(e))
        return []


async def search_places_with_diagnostics(
    query: str, destination_id: uuid.UUID, top_k: int = 10
) -> PlaceSearchOutcome:
    """Search with optional fusion diagnostics sidecar (does not alter hit order)."""
    settings = get_settings()
    want_diag = bool(settings.SEARCH_FUSION_DIAGNOSTICS)
    collection = places_collection()

    if not is_qdrant_available():
        diag = (
            _base_diagnostics(
                mode="unavailable",
                collection=collection,
                sparse_enabled=bool(settings.SEARCH_SPARSE_ENABLED),
                top_k=top_k,
            )
            if want_diag
            else None
        )
        return PlaceSearchOutcome(hits=[], diagnostics=diag)

    vector = await embed_text(query)
    if not vector:
        diag = (
            _base_diagnostics(
                mode="unavailable",
                collection=collection,
                sparse_enabled=bool(settings.SEARCH_SPARSE_ENABLED),
                top_k=top_k,
            )
            if want_diag
            else None
        )
        return PlaceSearchOutcome(hits=[], diagnostics=diag)

    try:
        client = get_qdrant_client()
        dest_filter = _destination_filter(destination_id)
        hybrid = collection_uses_hybrid_schema()
        use_rrf = (
            hybrid
            and settings.SEARCH_SPARSE_ENABLED
            and is_sparse_available()
        )
        sparse_q = encode_sparse(query) if use_rrf else None
        timeout = settings.QDRANT_OPERATION_TIMEOUT_SECONDS

        if use_rrf and sparse_q is not None and sparse_q.indices:
            log.debug(
                "qdrant.hybrid_rrf",
                rrf_k=settings.SEARCH_RRF_K,
                collection=collection,
            )
            response = await asyncio.wait_for(
                client.query_points(
                    collection_name=collection,
                    prefetch=[
                        qmodels.Prefetch(
                            query=vector,
                            using="dense",
                            limit=top_k * 2,
                            filter=dest_filter,
                        ),
                        qmodels.Prefetch(
                            query=sparse_q,
                            using="bm25",
                            limit=top_k * 2,
                            filter=dest_filter,
                        ),
                    ],
                    query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
                    limit=top_k,
                ),
                timeout=timeout,
            )
            hits = _hits_from_points(list(response.points or []))
            diagnostics: dict[str, Any] | None = None
            if want_diag:
                fused_ids = _place_ids(hits)
                dense_ids = await _query_place_ids_fail_soft(
                    client=client,
                    collection=collection,
                    timeout=timeout,
                    query=vector,
                    using="dense",
                    dest_filter=dest_filter,
                    limit=top_k,
                )
                sparse_ids = await _query_place_ids_fail_soft(
                    client=client,
                    collection=collection,
                    timeout=timeout,
                    query=sparse_q,
                    using="bm25",
                    dest_filter=dest_filter,
                    limit=top_k,
                )
                diagnostics = _base_diagnostics(
                    mode="hybrid_rrf",
                    collection=collection,
                    sparse_enabled=True,
                    top_k=top_k,
                    fused_place_ids=fused_ids,
                    dense_place_ids=dense_ids,
                    sparse_place_ids=sparse_ids,
                )
            return PlaceSearchOutcome(hits=hits, diagnostics=diagnostics)

        kwargs: dict[str, Any] = {
            "collection_name": collection,
            "query": vector,
            "query_filter": dest_filter,
            "limit": top_k,
        }
        if hybrid:
            kwargs["using"] = "dense"
        response = await asyncio.wait_for(
            client.query_points(**kwargs),
            timeout=timeout,
        )
        hits = _hits_from_points(list(response.points or []))
        diagnostics = None
        if want_diag:
            fused_ids = _place_ids(hits)
            diagnostics = _base_diagnostics(
                mode="dense_only",
                collection=collection,
                sparse_enabled=bool(settings.SEARCH_SPARSE_ENABLED),
                top_k=top_k,
                fused_place_ids=fused_ids,
                dense_place_ids=fused_ids,
                sparse_place_ids=[],
            )
        return PlaceSearchOutcome(hits=hits, diagnostics=diagnostics)
    except Exception as e:
        log.warning("qdrant.search_failed", error=str(e))
        diag = (
            _base_diagnostics(
                mode="unavailable",
                collection=collection,
                sparse_enabled=bool(settings.SEARCH_SPARSE_ENABLED),
                top_k=top_k,
            )
            if want_diag
            else None
        )
        return PlaceSearchOutcome(hits=[], diagnostics=diag)


async def search_places(
    query: str, destination_id: uuid.UUID, top_k: int = 10
) -> list[PlaceSearchResult]:
    """Destination-scoped place search — returns hits only (backward compatible)."""
    outcome = await search_places_with_diagnostics(query, destination_id, top_k=top_k)
    return outcome.hits


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
                collection_name=places_collection(),
                count_filter=_destination_filter(destination_id),
            ),
            timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
        )
        return result.count
    except Exception as e:
        log.warning("qdrant.count_failed", error=str(e))
        return 0
