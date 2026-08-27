"""Fixed LLM bookend: parse trip preferences before the tool loop (P5.8)."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.runnables import RunnableConfig

from src.core.exceptions import WandrLLMError
from src.core.llm.client import chat_completion, merge_token_usage
from src.places.constants import PLACE_TAG_VOCAB

_DEFAULT_DAYS = 3
_DEFAULT_BUDGET = "mid"

_INTEREST_ALIASES: dict[str, str] = {
    "photo": "photography",
    "photos": "photography",
    "photograph": "photography",
    "photography": "photography",
    "offbeat": "offbeat",
    "hidden": "offbeat",
    "trek": "trek",
    "trekking": "trek",
    "hike": "trek",
    "hiking": "trek",
    "viewpoint": "viewpoint",
    "views": "viewpoint",
    "monastery": "monastery",
    "temple": "monastery",
    "cultural": "cultural",
    "culture": "cultural",
    "family": "family",
    "nature": "nature",
    "adventure": "adventure",
}

_VOCAB_SET = {t.lower() for t in PLACE_TAG_VOCAB}

_PARSE_SYSTEM = (
    "Extract trip preferences as JSON with keys: "
    "days (int), budget (string: budget|mid|luxury), "
    "interests (array of strings), include_offbeat (bool), include_trekking (bool). "
    "Respond with JSON only."
)


def _defaults(llm_retry_count: int) -> dict[str, Any]:
    return {
        "days": _DEFAULT_DAYS,
        "budget": _DEFAULT_BUDGET,
        "interests": [],
        "include_offbeat": False,
        "include_trekking": False,
        "llm_retry_count": llm_retry_count + 1,
    }


def _map_interest(raw: str) -> str:
    key = raw.strip().lower()
    if not key:
        return raw
    if key in _INTEREST_ALIASES:
        return _INTEREST_ALIASES[key]
    if key in _VOCAB_SET:
        # Preserve canonical vocab casing from PLACE_TAG_VOCAB
        for tag in PLACE_TAG_VOCAB:
            if tag.lower() == key:
                return tag
    return raw.strip()


def _normalize_interests(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()

    def _add(mapped: str) -> None:
        key = mapped.lower()
        if not key or key in seen:
            return
        seen.add(key)
        out.append(mapped)

    for item in raw:
        if not isinstance(item, str):
            continue
        # LLM may return compound phrases ("offbeat photography") — split tokens.
        parts = [p for p in re.split(r"[\s,/|;]+", item.strip()) if p]
        if not parts:
            continue
        if len(parts) == 1:
            _add(_map_interest(parts[0]))
            continue
        mapped_any = False
        for part in parts:
            mapped = _map_interest(part)
            # Only keep tokens that resolve to known vocab/aliases (drop junk words).
            if mapped.lower() in _VOCAB_SET or part.strip().lower() in _INTEREST_ALIASES:
                _add(mapped)
                mapped_any = True
        if not mapped_any:
            _add(_map_interest(item))
    return out


def _coerce_days(value: Any) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        return _DEFAULT_DAYS
    return days if days > 0 else _DEFAULT_DAYS


def _parse_json_content(content: str | None) -> dict[str, Any] | None:
    if not content or not str(content).strip():
        return None
    text = str(content).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _prefs_payload(update: dict[str, Any]) -> dict[str, Any]:
    return {
        "interests": update.get("interests") or [],
        "budget": update.get("budget"),
        "days": update.get("days"),
        "include_offbeat": update.get("include_offbeat"),
        "include_trekking": update.get("include_trekking"),
    }


async def parse_preferences(
    state: dict[str, Any],
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """Parse raw_input into prefs via chat_completion; defaults on failure."""
    raw_input = (state or {}).get("raw_input") or ""
    llm_retry_count = int((state or {}).get("llm_retry_count") or 0)
    token_usage = dict((state or {}).get("token_usage") or {})

    configurable = config.get("configurable") if config else None
    if not isinstance(configurable, dict):
        configurable = {}
    emit = configurable.get("emit")

    try:
        result = await chat_completion(
            messages=[
                {"role": "system", "content": _PARSE_SYSTEM},
                {"role": "user", "content": str(raw_input)},
            ],
            response_format={"type": "json_object"},
        )
        token_usage = merge_token_usage(token_usage, result.usage)
        llm_retry_count += int(result.retry_count or 0)
        content = result.content
        parsed = _parse_json_content(content)
        if parsed is None:
            update = _defaults(llm_retry_count)
        else:
            interests = _normalize_interests(parsed.get("interests"))
            include_offbeat = bool(parsed.get("include_offbeat", False))
            include_trekking = bool(parsed.get("include_trekking", False))
            interest_keys = {i.lower() for i in interests}
            if "offbeat" in interest_keys:
                include_offbeat = True
            if "trek" in interest_keys:
                include_trekking = True

            budget = parsed.get("budget")
            if not isinstance(budget, str) or not budget.strip():
                budget = _DEFAULT_BUDGET

            update = {
                "days": _coerce_days(parsed.get("days")),
                "budget": budget.strip().lower(),
                "interests": interests,
                "include_offbeat": include_offbeat,
                "include_trekking": include_trekking,
                "llm_retry_count": llm_retry_count,
            }
    except WandrLLMError:
        update = _defaults(llm_retry_count)

    update["token_usage"] = token_usage

    if callable(emit):
        snapshot = {**(state or {}), **update}
        emit("preferences_done", _prefs_payload(update), state_snapshot=snapshot)
    return update
