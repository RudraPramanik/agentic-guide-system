"""Bounded OSM opening-hours grammar. No package and no clock read."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.travel_engine.place_selector import PlaceCandidate

HoursStatus = Literal["verified", "unknown", "malformed"]

_VERIFIED_WINDOW = re.compile(
    r"^Mo-Su ([01]\d|2[0-3]):([0-5]\d)-(([01]\d|2[0-3]):([0-5]\d)|24:00)$"
)
_CLOSED = re.compile(r"^(?i:off|closed)$")
_RESTRICTED = re.compile(
    r"\b(Mo|Tu|We|Th|Fr|Sa|Su|PH|SH|sunrise|sunset|dawn|dusk|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b"
)


@dataclass(frozen=True)
class ParsedHours:
    status: HoursStatus
    raw: str | None
    opening_open: str | None
    opening_close: str | None


def _minutes(hours: str, minutes: str) -> int:
    return int(hours) * 60 + int(minutes)


def parse_opening_hours(raw: str | None) -> ParsedHours:
    if raw is None or raw.strip() == "":
        return ParsedHours("unknown", None, None, None)
    text = raw.strip()
    if text == "24/7":
        return ParsedHours("verified", text, "00:00", "24:00")
    if _CLOSED.fullmatch(text):
        return ParsedHours("verified", text, "00:00", "00:00")
    match = _VERIFIED_WINDOW.fullmatch(text)
    if match:
        open_h, open_m = match.group(1), match.group(2)
        if match.group(3) == "24:00":
            close_min = 24 * 60
            close = "24:00"
        else:
            close_h, close_m = match.group(4), match.group(5)
            close_min = _minutes(close_h, close_m)
            close = f"{close_h}:{close_m}"
        if close_min > _minutes(open_h, open_m):
            return ParsedHours("verified", text, f"{open_h}:{open_m}", close)
    if _RESTRICTED.search(text):
        return ParsedHours("unknown", text, None, None)
    return ParsedHours("malformed", text, None, None)


def apply_hours(
    candidate: PlaceCandidate,
    tags: dict | None,
    enabled: bool,
) -> PlaceCandidate:
    """Copy parsed hours onto a candidate. Flag off leaves the defaults."""
    if not enabled:
        return candidate
    raw = None
    if isinstance(tags, dict):
        value = tags.get("opening_hours")
        if isinstance(value, str):
            raw = value
    parsed = parse_opening_hours(raw)
    return candidate.model_copy(
        update={
            "opening_hours_status": parsed.status,
            "opening_open": parsed.opening_open,
            "opening_close": parsed.opening_close,
            "opening_hours_raw": parsed.raw,
        }
    )
