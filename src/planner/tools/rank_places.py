"""rank_places — DISCOVER; travel_engine select_places (no LLM when flag off)."""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.planner.tools._helpers import (
    dict_to_candidate,
    preferences_from_state,
    scored_to_dict,
    state_get,
)
from src.planner.tools.constants import RANK_EXPLANATION_TOP_N
from src.planner.tools.schemas import RankPlacesIn, ToolResult
from src.travel_engine.place_selector import explain_selection, rank_candidates


def _base_coords(state: Any) -> tuple[float | None, float | None]:
    lat = state_get(state, "base_lat")
    lng = state_get(state, "base_lng")
    if lat is None or lng is None:
        return None, None
    return float(lat), float(lng)


def _append_reasoning_note(ctx: Any, note: dict[str, Any]) -> None:
    if ctx is None:
        return
    notes = getattr(ctx, "reasoning_notes", None)
    if notes is None:
        ctx.reasoning_notes = [note]
    else:
        notes.append(note)


async def run(
    inp: RankPlacesIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    raw = state_get(state, "candidate_pois") or []
    candidates = [dict_to_candidate(c) if isinstance(c, dict) else c for c in raw]
    prefs = preferences_from_state(state)
    settings = get_settings()
    v2_enabled = bool(settings.TRAVEL_ENGINE_V2_ENABLED)
    base_lat, base_lng = _base_coords(state)
    priorities = None

    if settings.REASONING_LAYER_ENABLED:
        from src.planner.reasoning.budget import InvocationBudget
        from src.planner.reasoning.experience_reasoner import run_experience_reasoner

        budget = InvocationBudget()
        # Share budget across the generate via ToolContext when present.
        existing = getattr(ctx, "reasoning_budget", None) if ctx is not None else None
        if existing is not None:
            budget = existing
        elif ctx is not None:
            ctx.reasoning_budget = budget

        cand_dicts = [
            c if isinstance(c, dict) else c.model_dump(mode="json")
            for c in (raw if isinstance(raw, list) else [])
        ]
        reasoner = await run_experience_reasoner(
            raw_input=str(state_get(state, "raw_input") or ""),
            candidates=cand_dicts,
            budget=budget,
            mode="live",
        )
        if not reasoner.skipped:
            priorities = reasoner.priorities
        _append_reasoning_note(
            ctx,
            {
                "name": "experience_reasoner",
                "ok": not reasoner.skipped,
                "code": reasoner.reason,
                "ms": reasoner.ms,
                "diagnostics": reasoner.as_trace_diagnostics(),
                "usage": reasoner.usage,
            },
        )

    ranked = rank_candidates(
        candidates,
        prefs,
        v2_enabled=v2_enabled,
        base_lat=base_lat,
        base_lng=base_lng,
        priorities=priorities,
    )
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
