"""rank_places — DISCOVER; travel_engine select_places (no LLM)."""

from __future__ import annotations

from typing import Any

from src.planner.tools._helpers import (
    dict_to_candidate,
    preferences_from_state,
    scored_to_dict,
    state_get,
)
from src.planner.tools.constants import RANK_EXPLANATION_TOP_N
from src.planner.tools.schemas import RankPlacesIn, ToolResult
from src.travel_engine.place_selector import explain_selection, select_places


async def run(
    inp: RankPlacesIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    _ = ctx
    raw = state_get(state, "candidate_pois") or []
    candidates = [dict_to_candidate(c) if isinstance(c, dict) else c for c in raw]
    prefs = preferences_from_state(state)
    ranked = select_places(candidates, prefs)
    explanations = [
        explain_selection(s.place, s.score_breakdown)
        for s in ranked[:RANK_EXPLANATION_TOP_N]
    ]
    return ToolResult(
        ok=True,
        data={
            "ranked_pois": [scored_to_dict(s) for s in ranked],
            "explanations": explanations,
        },
    )
