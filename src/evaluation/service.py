"""Evaluation service — record planner generation outcomes (P5.10)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.evaluation.repository import EvaluationRepository


def _as_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _places_per_day(state: dict[str, Any]) -> list:
    itinerary = state.get("itinerary") or {}
    if isinstance(itinerary, dict):
        days = itinerary.get("days")
        if isinstance(days, list):
            return days
    schedule = state.get("schedule")
    if isinstance(schedule, list):
        return schedule
    return []


def _validation_flags(state: dict[str, Any]) -> tuple[bool, list]:
    vr = state.get("validation_result")
    if isinstance(vr, dict):
        passed = bool(vr.get("passed") or vr.get("ok") or False)
        warnings = vr.get("warnings") or []
        if not isinstance(warnings, list):
            warnings = [warnings] if warnings else []
        return passed, warnings
    if state.get("last_validate_ok"):
        return True, []
    return False, []


def _phase_str(state: dict[str, Any]) -> str:
    phase = state.get("agent_phase") or "discover"
    return getattr(phase, "value", None) or str(phase)


class EvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EvaluationRepository(session)

    async def record_generation(self, state: dict[str, Any]) -> Any:
        """Map TravelState → TripEvaluation columns and persist (flush only)."""
        settings = get_settings()
        destination_id = _as_uuid(state.get("destination_id"))
        if destination_id is None:
            raise ValueError("destination_id required for evaluation")

        prefs = {
            "days": state.get("days"),
            "budget": state.get("budget"),
            "interests": state.get("interests") or [],
            "include_offbeat": state.get("include_offbeat"),
            "include_trekking": state.get("include_trekking"),
        }
        validation_passed, validation_warnings = _validation_flags(state)
        candidates = state.get("candidate_pois") or []
        ranked = state.get("ranked_pois") or []
        route = state.get("route")
        if route is None:
            route = {}
        elif not isinstance(route, dict):
            route = {"days": route}

        data = {
            "trip_id": _as_uuid(state.get("trip_id")),
            "destination_id": destination_id,
            "raw_input": str(state.get("raw_input") or ""),
            "parsed_preferences": prefs,
            "candidates_retrieved": len(candidates) if hasattr(candidates, "__len__") else 0,
            "candidates_after_ranking": len(ranked) if hasattr(ranked, "__len__") else 0,
            "final_route": route if isinstance(route, dict) else {"value": route},
            "places_per_day": _places_per_day(state),
            "total_distance_km": float(state.get("total_distance_km") or 0.0),
            "base_lat": float(state.get("base_lat") or 0.0),
            "base_lng": float(state.get("base_lng") or 0.0),
            "generation_time_ms": int(state.get("generation_time_ms") or 0),
            "token_usage": state.get("token_usage") or {},
            "llm_model": str(state.get("llm_model") or settings.LLM_MODEL),
            "llm_retry_count": int(state.get("llm_retry_count") or 0),
            "tool_loop_count": int(state.get("tool_loop_count") or 0),
            "tool_trace": list(state.get("tool_trace") or []),
            "agent_phase_reached": _phase_str(state),
            "readiness_score": state.get("readiness_score"),
            "used_geo_fallback": bool(state.get("used_geo_fallback") or False),
            "used_osrm_fallback": bool(state.get("used_osrm_fallback") or False),
            "abort_triggered": bool(state.get("abort_triggered") or False),
            "validation_passed": validation_passed,
            "validation_warnings": validation_warnings,
        }
        return await self.repo.create_generation(data)
