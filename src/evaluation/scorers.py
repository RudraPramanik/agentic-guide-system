"""Pure golden-eval scorers — no LLM, network, or DB I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def _place_names(result: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    itinerary = result.get("itinerary") or {}
    days = itinerary.get("days") if isinstance(itinerary, dict) else None
    if not isinstance(days, list):
        days = result.get("schedule") if isinstance(result.get("schedule"), list) else []
    for day in days or []:
        if not isinstance(day, dict):
            continue
        for stop in day.get("stops") or day.get("places") or []:
            if isinstance(stop, dict) and stop.get("name"):
                names.add(str(stop["name"]).strip().lower())
        # candidates / ranked may also carry names
    for key in ("candidate_pois", "ranked_pois"):
        for item in result.get(key) or []:
            if isinstance(item, dict) and item.get("name"):
                names.add(str(item["name"]).strip().lower())
            elif hasattr(item, "name") and getattr(item, "name"):
                names.add(str(getattr(item, "name")).strip().lower())
    return names


def _validation_passed(result: dict[str, Any]) -> bool:
    vr = result.get("validation_result")
    if isinstance(vr, dict):
        return bool(vr.get("passed") or vr.get("ok") or False)
    if hasattr(vr, "ok"):
        return bool(getattr(vr, "ok"))
    if hasattr(vr, "passed"):
        return bool(getattr(vr, "passed"))
    return bool(result.get("last_validate_ok"))


def score_case(result: dict[str, Any], case: dict[str, Any]) -> Verdict:
    """Score a generation result against a golden case. Pure / deterministic."""
    reasons: list[str] = []
    assertions = case.get("assertions") or {}
    if not isinstance(assertions, dict):
        return Verdict(False, ["assertions must be an object"])

    must = case.get("must_include_places") or []
    if must:
        names = _place_names(result)
        for place in must:
            if str(place).strip().lower() not in names:
                reasons.append(f"missing_place:{place}")

    if "validation_passed" in assertions:
        expected = bool(assertions["validation_passed"])
        actual = _validation_passed(result)
        if actual != expected:
            reasons.append(
                f"validation_passed:expected={expected}:actual={actual}"
            )

    if "max_days" in assertions:
        max_days = int(assertions["max_days"])
        days = result.get("days")
        if days is not None and int(days) > max_days:
            reasons.append(f"max_days:expected<={max_days}:actual={days}")
        itinerary = result.get("itinerary") or {}
        day_list = itinerary.get("days") if isinstance(itinerary, dict) else None
        if isinstance(day_list, list) and len(day_list) > max_days:
            reasons.append(
                f"itinerary_days:expected<={max_days}:actual={len(day_list)}"
            )

    if "min_places_per_day" in assertions:
        min_p = int(assertions["min_places_per_day"])
        itinerary = result.get("itinerary") or {}
        day_list = itinerary.get("days") if isinstance(itinerary, dict) else None
        schedule = result.get("schedule") if isinstance(result.get("schedule"), list) else None
        days_src = day_list if isinstance(day_list, list) else schedule
        if isinstance(days_src, list) and days_src:
            for day in days_src:
                if not isinstance(day, dict):
                    continue
                stops = day.get("stops") or day.get("places") or []
                if len(stops) < min_p:
                    reasons.append(
                        f"min_places_per_day:day={day.get('day')}:actual={len(stops)}"
                    )

    if "readiness_score_min" in assertions:
        floor = float(assertions["readiness_score_min"])
        score = result.get("readiness_score")
        if score is None or float(score) < floor:
            reasons.append(
                f"readiness_score_min:expected>={floor}:actual={score}"
            )

    if assertions.get("no_geo_fallback") is True:
        if result.get("used_geo_fallback"):
            reasons.append("no_geo_fallback:used_geo_fallback=True")

    if "max_tool_calls" in assertions:
        max_tools = int(assertions["max_tool_calls"])
        loop = int(result.get("tool_loop_count") or 0)
        if loop > max_tools:
            reasons.append(f"max_tool_calls:expected<={max_tools}:actual={loop}")

    return Verdict(passed=len(reasons) == 0, reasons=reasons)
