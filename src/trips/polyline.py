"""Pure Google-encoded polyline decode — no network, no third-party package."""

from __future__ import annotations


def decode_polyline(encoded: str | None) -> list[tuple[float, float]]:
    """
    Decode a Google-encoded polyline into (lat, lng) pairs.
    Empty, None, or invalid input → [] (never raises).
    """
    if not encoded or not isinstance(encoded, str):
        return []
    try:
        coordinates: list[tuple[float, float]] = []
        index = 0
        lat = 0
        lng = 0
        length = len(encoded)

        while index < length:
            result = 0
            shift = 0
            while True:
                if index >= length:
                    return []
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            dlat = ~(result >> 1) if result & 1 else (result >> 1)
            lat += dlat

            result = 0
            shift = 0
            while True:
                if index >= length:
                    return []
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            dlng = ~(result >> 1) if result & 1 else (result >> 1)
            lng += dlng

            coordinates.append((lat / 1e5, lng / 1e5))

        return coordinates
    except Exception:
        return []
