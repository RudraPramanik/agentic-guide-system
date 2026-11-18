"""Flag-on search_places PostGIS fallback uses search area, not 30 km."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.location_intelligence.schemas import LocationType, ResolvedLocation, SearchArea
from src.planner.tools import search_places as sp
from src.planner.tools.schemas import SearchPlacesIn


@pytest.mark.asyncio
async def test_geo_fallback_uses_area_radius_not_thirty() -> None:
    dest_id = uuid4()
    area = SearchArea(
        strategy="radius",
        anchor=ResolvedLocation(
            canonical_name="Pin",
            location_type=LocationType.MAP_PIN,
            lat=27.5,
            lng=88.5,
            provider="user",
            provider_id=None,
            confidence=1.0,
            explanation="pin",
        ),
        radius_km=10.0,
        boundary_geojson=None,
        fallback_used=False,
        description="10",
    )
    state = {
        "destination_id": str(dest_id),
        "base_lat": 27.0,
        "base_lng": 88.0,
        "search_area": area.model_dump(mode="json"),
        "raw_input": "tea",
    }
    outcome = SimpleNamespace(hits=[], diagnostics=None)
    repo = MagicMock()
    repo.find_within_radius = AsyncMock(return_value=[])
    session = MagicMock()

    with (
        patch.object(
            sp.places_index,
            "search_places_with_diagnostics",
            AsyncMock(return_value=outcome),
        ),
        patch.object(sp, "_destination_country", AsyncMock(return_value="IN")),
        patch.object(sp, "PlaceRepository", return_value=repo),
    ):
        ctx = SimpleNamespace(
            destination_id=dest_id,
            base_lat=27.0,
            base_lng=88.0,
            db=session,
        )
        result = await sp.run(SearchPlacesIn(query="tea"), ctx=ctx, state=state)

    assert result.ok is True
    repo.find_within_radius.assert_awaited()
    args = repo.find_within_radius.await_args.args
    assert args[0] == pytest.approx(27.5)
    assert args[1] == pytest.approx(88.5)
    assert args[2] == pytest.approx(10.0)
