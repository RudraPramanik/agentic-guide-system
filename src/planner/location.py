"""Flag-on mapping from PlanRequest → discovery_anchor + SearchArea dicts."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.destinations.models import Destination
from src.destinations.service import DestinationService
from src.location_intelligence.exceptions import (
    AnchorNotConfirmedError,
    InvalidCoordinatesError,
    LocationIntelligenceError,
    OversizedAdminError,
    as_http_error,
)
from src.location_intelligence.map_pin import map_pin_location
from src.location_intelligence.schemas import LocationType, ResolvedLocation, SearchArea
from src.location_intelligence.service import LocationIntelligenceService
from src.planner.schemas import PlanRequest


def _area_dicts(
    anchor: ResolvedLocation, area: SearchArea
) -> tuple[dict[str, Any], dict[str, Any]]:
    return anchor.model_dump(mode="json"), area.model_dump(mode="json")


async def build_generate_location(
    body: PlanRequest,
    dest: Destination,
    session: AsyncSession,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build server-owned anchor + search area for LOCATION_V2_ENABLED generate.

    Raises LocationValidationError (422) subclasses on failure.
    """
    svc = LocationIntelligenceService(session=session)
    dest_svc = DestinationService(session)

    posted = body.discovery_anchor
    if posted is None:
        # Destination rows have no bbox → city fallback radius, disclosed.
        anchor = dest_svc.to_city_anchor(dest)
        area = svc.search_area_for(anchor)
        return _area_dicts(anchor, area)

    try:
        if posted.provider == "user" or posted.location_type == LocationType.MAP_PIN.value:
            anchor = map_pin_location(
                posted.lat,
                posted.lng,
                canonical_name=posted.canonical_name or "Map pin",
            )
            area = svc.search_area_for(anchor, user_radius_km=body.radius_km)
            return _area_dicts(anchor, area)

        query = (posted.query or posted.canonical_name or "").strip()
        if not query:
            raise AnchorNotConfirmedError("query or canonical_name required")
        if posted.provider_id is None:
            raise AnchorNotConfirmedError("provider_id required for confirmation")

        resolution = await svc.search(query)
        if resolution.status == "not_found" and resolution.reason == "geocoder_timeout":
            raise AnchorNotConfirmedError("geocoder_timeout")

        selected: ResolvedLocation | None = None
        for candidate in resolution.candidates:
            if (
                candidate.provider == posted.provider
                and candidate.provider_id == posted.provider_id
            ):
                selected = candidate
                break
        if selected is None:
            raise AnchorNotConfirmedError()

        if selected.location_type in (LocationType.COUNTRY, LocationType.REGION):
            raise as_http_error(OversizedAdminError(selected.location_type.value))

        area = svc.search_area_for(selected, user_radius_km=body.radius_km)
        # Posted radius replaces policy radius only when strategy is radius.
        if area.strategy != "radius" and body.radius_km is not None:
            # Keep boundary; radius_km on body is ignored for boundaries.
            pass
        return _area_dicts(selected, area)
    except LocationIntelligenceError as exc:
        raise as_http_error(exc) from exc
    except InvalidCoordinatesError:
        raise
    except AnchorNotConfirmedError:
        raise
