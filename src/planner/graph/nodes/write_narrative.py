"""Fixed narrative bookend — day titles/paragraphs only; never mutates geometry (P5.10)."""

from __future__ import annotations

import json
import re
from typing import Any

from src.core.exceptions import WandrLLMError
from src.core.llm.client import chat_completion

_NARRATIVE_SYSTEM = (
    "You write travel day titles and short paragraphs only. "
    "Respond with JSON: {\"days\": [{\"day\": 1, \"title\": \"...\", \"narrative\": \"...\"}]}. "
    "Do not invent place IDs, coordinates, stop order, or times. "
    "Do not add or remove stops."
)


def _schedule_days(schedule: Any) -> list[Any]:
    if isinstance(schedule, list):
        return schedule
    if isinstance(schedule, dict):
        days = schedule.get("days")
        if isinstance(days, list):
            return days
    return []


def _place_ids_in_schedule(schedule: Any) -> set[str]:
    ids: set[str] = set()
    for day in _schedule_days(schedule):
        if not isinstance(day, dict):
            continue
        stops = day.get("stops") or day.get("places") or []
        if not isinstance(stops, list):
            continue
        for stop in stops:
            if not isinstance(stop, dict):
                continue
            pid = stop.get("place_id")
            if pid is not None:
                ids.add(str(pid))
    return ids


def _template_days(schedule: Any, destination_name: str) -> list[dict[str, Any]]:
    days_out: list[dict[str, Any]] = []
    raw_days = _schedule_days(schedule)
    if not raw_days:
        return [
            {
                "day": 1,
                "title": f"Exploring {destination_name or 'your destination'}",
                "narrative": "A flexible day shaped around the planned stops.",
            }
        ]
    for i, day in enumerate(raw_days, start=1):
        day_num = i
        if isinstance(day, dict):
            day_num = int(day.get("day") or i)
        days_out.append(
            {
                "day": day_num,
                "title": f"Day {day_num} in {destination_name or 'destination'}",
                "narrative": f"Follow the planned stops for day {day_num}.",
            }
        )
    return days_out


def _strip_unknown_place_ids(text: str, allowed: set[str]) -> str:
    if not text or not allowed:
        return text

    def _repl(match: re.Match[str]) -> str:
        token = match.group(0)
        return token if token in allowed else ""

    # Strip bare UUID-looking tokens not in schedule
    return re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        _repl,
        text,
    )


def _parse_narrative_json(content: str | None, schedule: Any, allowed: set[str]) -> list[dict[str, Any]] | None:
    if not content or not str(content).strip():
        return None
    text = str(content).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    days = data.get("days")
    if not isinstance(days, list) or not days:
        return None
    out: list[dict[str, Any]] = []
    for i, item in enumerate(days, start=1):
        if not isinstance(item, dict):
            continue
        title = _strip_unknown_place_ids(str(item.get("title") or f"Day {i}"), allowed)
        narrative = _strip_unknown_place_ids(str(item.get("narrative") or ""), allowed)
        out.append(
            {
                "day": int(item.get("day") or i),
                "title": title.strip() or f"Day {i}",
                "narrative": narrative.strip(),
            }
        )
    return out or None


def _build_itinerary(
    state: dict[str, Any],
    day_narratives: list[dict[str, Any]],
) -> dict[str, Any]:
    """Combine locked schedule/route structure with narrative — geometry untouched."""
    schedule = state.get("schedule")
    route = state.get("route")
    days_struct = _schedule_days(schedule)
    narrative_by_day = {int(d["day"]): d for d in day_narratives if "day" in d}
    days_out: list[dict[str, Any]] = []

    if days_struct:
        for i, day in enumerate(days_struct, start=1):
            day_num = int(day.get("day") or i) if isinstance(day, dict) else i
            narr = narrative_by_day.get(day_num) or {
                "day": day_num,
                "title": f"Day {day_num}",
                "narrative": "",
            }
            entry: dict[str, Any] = {
                "day": day_num,
                "title": narr.get("title") or f"Day {day_num}",
                "narrative": narr.get("narrative") or "",
            }
            if isinstance(day, dict):
                # Preserve structure fields; never rewrite stop order/times/coords
                for key in ("stops", "places", "total_distance_km", "total_travel_min", "polyline"):
                    if key in day:
                        entry[key] = day[key]
            days_out.append(entry)
    else:
        days_out = list(day_narratives)

    return {
        "days": days_out,
        "route": route,
        "schedule": schedule,
        "destination_id": state.get("destination_id"),
        "destination_name": state.get("destination_name"),
    }


async def write_narrative(state: dict[str, Any]) -> dict[str, Any]:
    """Add day titles/paragraphs only; soft-fail to templates on LLM error."""
    schedule = state.get("schedule")
    destination_name = str(state.get("destination_name") or "")
    allowed = _place_ids_in_schedule(schedule)
    llm_retry_count = int(state.get("llm_retry_count") or 0)

    user_payload = {
        "destination": destination_name,
        "days": state.get("days"),
        "schedule_summary": schedule,
        "allowed_place_ids": sorted(allowed),
    }

    try:
        content = await chat_completion(
            messages=[
                {"role": "system", "content": _NARRATIVE_SYSTEM},
                {"role": "user", "content": json.dumps(user_payload, default=str)},
            ],
            response_format={"type": "json_object"},
        )
        parsed = _parse_narrative_json(content, schedule, allowed)
        if parsed is None:
            parsed = _template_days(schedule, destination_name)
            llm_retry_count += 1
        itinerary = _build_itinerary(state, parsed)
        return {"itinerary": itinerary, "llm_retry_count": llm_retry_count}
    except WandrLLMError:
        parsed = _template_days(schedule, destination_name)
        itinerary = _build_itinerary(state, parsed)
        return {
            "itinerary": itinerary,
            "llm_retry_count": llm_retry_count + 1,
        }
