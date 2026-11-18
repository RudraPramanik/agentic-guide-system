"""Shadow sampling — stable hash, no response change."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from src.config import get_settings
from src.planner.reasoning.budget import InvocationBudget
from src.planner.reasoning.critic import run_critic
from src.planner.reasoning.experience_reasoner import run_experience_reasoner
from src.planner.reasoning.schemas import CriticResult, ReasonerResult
from src.planner.tools._helpers import (
    dict_to_candidate,
    preferences_from_state,
)
from src.travel_engine.place_selector import rank_candidates

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_shadow_text(raw_input: str) -> str:
    return _WHITESPACE_RE.sub(" ", (raw_input or "").strip())


def is_shadow_selected(
    *,
    session_id: str,
    destination_id: UUID | str,
    raw_input: str,
    sample_rate: float | None = None,
) -> bool:
    settings = get_settings()
    if settings.REASONING_LAYER_ENABLED:
        return False
    rate = (
        float(settings.REASONING_SHADOW_SAMPLE_RATE)
        if sample_rate is None
        else float(sample_rate)
    )
    if rate <= 0.0:
        return False
    if rate >= 1.0:
        return True
    material = (
        f"{session_id}:{destination_id}:{normalize_shadow_text(raw_input)}"
    )
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big", signed=False)
    return (value / float(2**64)) < rate


async def run_shadow_pass(
    state: dict[str, Any],
    *,
    budget: InvocationBudget | None = None,
) -> tuple[ReasonerResult | None, CriticResult | None, list[Any] | None]:
    """Re-rank a copy and optionally critique. Does not mutate ``state``."""
    settings = get_settings()
    if settings.REASONING_LAYER_ENABLED:
        return None, None, None
    if not is_shadow_selected(
        session_id=str(state.get("session_id") or ""),
        destination_id=str(state.get("destination_id") or ""),
        raw_input=str(state.get("raw_input") or ""),
    ):
        return None, None, None

    local_budget = budget or InvocationBudget()
    candidates = list(state.get("candidate_pois") or [])
    reasoner = await run_experience_reasoner(
        raw_input=str(state.get("raw_input") or ""),
        candidates=candidates,
        budget=local_budget,
        mode="shadow",
    )
    priorities = reasoner.priorities if not reasoner.skipped else {}
    pool = [dict_to_candidate(c) if isinstance(c, dict) else c for c in candidates]
    prefs = preferences_from_state(state)
    ranked = rank_candidates(
        pool,
        prefs,
        v2_enabled=bool(settings.TRAVEL_ENGINE_V2_ENABLED),
        base_lat=float(state["base_lat"]) if state.get("base_lat") is not None else None,
        base_lng=float(state["base_lng"]) if state.get("base_lng") is not None else None,
        priorities=priorities or None,
    )

    critic: CriticResult | None = None
    if local_budget.remaining() > 0:
        findings = []
        vr = state.get("validation_result")
        if isinstance(vr, dict):
            raw = vr.get("findings") or vr.get("v2_findings") or []
            if isinstance(raw, list):
                findings = list(raw)
        elif state.get("v2_findings"):
            findings = list(state.get("v2_findings") or [])
        evidence: list[Any] = []
        for c in candidates:
            if isinstance(c, dict) and c.get("evidence"):
                evidence.extend(list(c.get("evidence") or []))
        critic = await run_critic(
            raw_input=str(state.get("raw_input") or ""),
            search_area=state.get("search_area")
            if isinstance(state.get("search_area"), dict)
            else None,
            evidence_refs=evidence,
            itinerary=state.get("itinerary")
            if isinstance(state.get("itinerary"), dict)
            else {},
            findings=findings,
            budget=local_budget,
            mode="shadow",
        )
    return reasoner, critic, ranked
