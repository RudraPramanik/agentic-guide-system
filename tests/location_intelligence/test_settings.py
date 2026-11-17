"""Location settings defaults."""

from __future__ import annotations

from src.config import Settings


def test_location_settings_defaults() -> None:
    # Construct without env — required fields still needed.
    s = Settings(
        SECRET_KEY="test",
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        NOMINATIM_USER_AGENT="test/0.1 (test@example.com)",
    )
    assert s.LOCATION_V2_ENABLED is False
    assert s.LOCATION_AUTO_RESOLVE_CONFIDENCE == 0.90
    assert s.LOCATION_POI_RADIUS_KM == 10.0
    assert s.LOCATION_NEIGHBORHOOD_RADIUS_KM == 5.0
    assert s.LOCATION_CITY_FALLBACK_RADIUS_KM == 15.0
    assert s.LOCATION_MAX_RADIUS_KM == 50.0
