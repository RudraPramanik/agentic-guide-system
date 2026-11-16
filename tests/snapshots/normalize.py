"""Replace volatile ids and timestamps. Leave coordinates, counts, and order exact."""

from __future__ import annotations

import re
from typing import Any

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key == "session_id" and isinstance(item, str):
                normalized[key] = "<session>"
            else:
                normalized[key] = normalize(item)
        return normalized
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, str):
        if _UUID.match(value):
            return "<uuid>"
        if _DATETIME.match(value):
            return "<datetime>"
        return value
    return value
