"""Frozen readiness while vector search is unavailable."""

from __future__ import annotations

import pytest

from tests.snapshots.compare import assert_fixture
from tests.snapshots.seed import seed_destination


@pytest.mark.asyncio
async def test_readiness_without_vector_search_matches_fixture(client, db_session) -> None:
    dest = await seed_destination(
        db_session,
        name="Snapshot Ready",
        osm_place_id="relation/snapshot-ready",
        place_count=100,
        enriched_count=100,
        indexed_count=100,
    )

    response = await client.get(f"/api/v1/destinations/{dest.id}/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["tier"] in {"ready", "limited", "sparse"}
    assert_fixture("readiness.json", body)
