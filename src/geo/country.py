"""Country code helpers for destination-scoped place catalogs."""

from __future__ import annotations

import re

# ISO-ish two-letter when possible; Destination.country is usually upper country_code.
_ISO2 = re.compile(r"^[A-Za-z]{2}$")


def normalize_country(value: str | None) -> str | None:
    """Normalize a country token for comparison (ISO2 upper, else stripped upper)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "unknown":
        return None
    if _ISO2.match(text):
        return text.upper()
    return text.upper()


def countries_match(a: str | None, b: str | None) -> bool:
    na, nb = normalize_country(a), normalize_country(b)
    if na is None or nb is None:
        return False
    return na == nb


def country_from_tags(tags: dict | None) -> str | None:
    """Best-effort country from OSM/provider tags."""
    if not tags:
        return None
    for key in (
        "wandr:country",
        "addr:country",
        "country",
        "is_in:country_code",
        "ISO3166-1",
        "ISO3166-1:alpha2",
    ):
        raw = tags.get(key)
        if raw:
            return normalize_country(str(raw))
    return None
