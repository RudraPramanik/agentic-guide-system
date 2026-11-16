"""Frozen GET /api/v1/destinations/search on a catalog hit."""

from __future__ import annotations

import pytest

from tests.snapshots.compare import assert_fixture, load_request
from tests.snapshots.seed import seed_destination


@pytest.mark.asyncio
async def test_search_catalog_hit_matches_fixture(client, db_session, forbid_live_providers) -> None:
    request = load_request("destination-search.json")
    await seed_destination(
        db_session,
        name=request["q"],
        osm_place_id="relation/snapshot-harbor",
        place_count=4,
    )

    response = await client.get("/api/v1/destinations/search", params={"q": request["q"]})

    assert response.status_code == 200
    assert_fixture("destination-search.json", response.json())
    forbid_live_providers["geocode"].assert_not_called()
    forbid_live_providers["geocode_search"].assert_not_called()
