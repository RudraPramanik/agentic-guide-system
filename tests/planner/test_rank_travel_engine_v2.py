"""rank_places / build_route auto-rank honor TRAVEL_ENGINE_V2_ENABLED."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

import pytest

from src.planner.tools.schemas import BuildRouteIn, RankPlacesIn
from src.planner.tools import build_route as build_route_mod
from src.planner.tools import rank_places as rank_places_mod
from tests.travel_engine.fake_routing import FakeRoutingProvider


def _cand_dict(name: str, *, lat: float, lng: float, category: str = "monastery") -> dict:
    return {
        "id": str(uuid4()),
        "name": name,
        "category": category,
        "enriched_tags": [category],
        "lat": lat,
        "lng": lng,
    }


@pytest.mark.asyncio
async def test_rank_places_flag_off_skips_normalizer_keys() -> None:
    state = {
        "candidate_pois": [
            _cand_dict("Ghoom Monastery", lat=27.3300, lng=88.1300),
            _cand_dict("ghoom monastery", lat=27.3301, lng=88.1301),
        ],
        "preferences": {"interests": ["monastery"], "days": 2},
        "base_lat": 27.03,
        "base_lng": 88.26,
    }
    settings = SimpleNamespace(
        TRAVEL_ENGINE_V2_ENABLED=False,
        REASONING_LAYER_ENABLED=False,
    )
    with patch.object(rank_places_mod, "get_settings", return_value=settings):
        result = await rank_places_mod.run(RankPlacesIn(), state=state)
    assert result.ok is True
    ranked = result.data["ranked_pois"]
    assert len(ranked) == 1  # AVOID_SAME_DAY
    breakdown = ranked[0]["score_breakdown"]
    assert "diversity" not in breakdown


@pytest.mark.asyncio
async def test_rank_places_flag_on_normalizes_variants() -> None:
    state = {
        "candidate_pois": [
            _cand_dict("Ghoom Monastery", lat=27.3300, lng=88.1300),
            _cand_dict("ghoom monastery", lat=27.3301, lng=88.1301),
            _cand_dict("Tiger Hill", lat=27.04, lng=88.26, category="viewpoint"),
        ],
        "preferences": {"interests": ["monastery", "viewpoint"], "days": 2},
        "base_lat": 27.03,
        "base_lng": 88.26,
    }
    settings = SimpleNamespace(
        TRAVEL_ENGINE_V2_ENABLED=True,
        REASONING_LAYER_ENABLED=False,
    )
    with patch.object(rank_places_mod, "get_settings", return_value=settings):
        result = await rank_places_mod.run(RankPlacesIn(), state=state)
    assert result.ok is True
    names = {row["place"]["name"] for row in result.data["ranked_pois"]}
    # One monastery survivor + Tiger Hill
    assert "Tiger Hill" in names
    monastery_names = [n for n in names if "monastery" in n.lower() or "ghoom" in n.lower()]
    assert len(monastery_names) == 1
    # V2 breakdown present on at least one row
    assert any("diversity" in row["score_breakdown"] for row in result.data["ranked_pois"])


@pytest.mark.asyncio
async def test_build_route_autorank_flag_off() -> None:
    state = {
        "ranked_pois": [],
        "candidate_pois": [
            _cand_dict("Alpha Park", lat=27.04, lng=88.26, category="park"),
            _cand_dict("Beta Museum", lat=27.05, lng=88.27, category="museum"),
        ],
        "preferences": {"interests": ["nature", "cultural"], "days": 1},
        "base_lat": 27.03,
        "base_lng": 88.26,
    }
    # Enrich tags so scoring has something to match
    state["candidate_pois"][0]["enriched_tags"] = ["nature"]
    state["candidate_pois"][1]["enriched_tags"] = ["cultural"]
    ctx = SimpleNamespace(
        routing=FakeRoutingProvider(default_duration_min=10, default_distance_km=1.0),
        base_lat=27.03,
        base_lng=88.26,
    )
    settings = SimpleNamespace(TRAVEL_ENGINE_V2_ENABLED=False)
    with patch.object(build_route_mod, "get_settings", return_value=settings):
        result = await build_route_mod.run(BuildRouteIn(), ctx=ctx, state=state)
    assert result.ok is True
    ranked = result.data["ranked_pois"]
    assert len(ranked) >= 1
    assert "diversity" not in ranked[0]["score_breakdown"]


@pytest.mark.asyncio
async def test_build_route_autorank_flag_on_uses_v2() -> None:
    state = {
        "ranked_pois": [],
        "candidate_pois": [
            _cand_dict("Ghoom Monastery", lat=27.3300, lng=88.1300),
            _cand_dict("ghoom monastery", lat=27.3301, lng=88.1301),
        ],
        "preferences": {"interests": ["monastery"], "days": 1},
        "base_lat": 27.03,
        "base_lng": 88.26,
    }
    ctx = SimpleNamespace(
        routing=FakeRoutingProvider(default_duration_min=10, default_distance_km=1.0),
        base_lat=27.03,
        base_lng=88.26,
    )
    settings = SimpleNamespace(TRAVEL_ENGINE_V2_ENABLED=True)
    with patch.object(build_route_mod, "get_settings", return_value=settings):
        result = await build_route_mod.run(BuildRouteIn(), ctx=ctx, state=state)
    assert result.ok is True
    ranked = result.data["ranked_pois"]
    assert len(ranked) == 1
    assert "diversity" in ranked[0]["score_breakdown"]
