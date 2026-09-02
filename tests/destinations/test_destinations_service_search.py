"""DestinationService.search unit tests — no DB."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import ExternalServiceError
from src.destinations.exceptions import DestinationNotFoundError
from src.destinations.service import DestinationService


@pytest.mark.asyncio
async def test_search_geocode_none_raises_not_found(mocker) -> None:
    session = MagicMock()
    service = DestinationService(session)
    service.repo = MagicMock()
    service.repo.search_by_name = AsyncMock(return_value=[])
    mocker.patch(
        "src.destinations.service.geocode",
        new=AsyncMock(return_value=None),
    )
    mocker.patch(
        "src.destinations.service.get_settings",
        return_value=MagicMock(SEARCH_GEOCODE_TIMEOUT_SECONDS=8.0),
    )

    with pytest.raises(DestinationNotFoundError):
        await service.search("XyzzyNonexistent999")


@pytest.mark.asyncio
async def test_search_geocode_upstream_raises_external_service(mocker) -> None:
    session = MagicMock()
    service = DestinationService(session)
    service.repo = MagicMock()
    service.repo.search_by_name = AsyncMock(return_value=[])
    mocker.patch(
        "src.destinations.service.geocode",
        new=AsyncMock(
            side_effect=ExternalServiceError(
                service="nominatim",
                message="Geocoding service rejected the request",
                details={"status_code": 403},
            )
        ),
    )
    mocker.patch(
        "src.destinations.service.get_settings",
        return_value=MagicMock(SEARCH_GEOCODE_TIMEOUT_SECONDS=8.0),
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await service.search("London")

    assert exc_info.value.details["service"] == "nominatim"
    assert exc_info.value.status_code == 502
    assert not isinstance(exc_info.value, DestinationNotFoundError)
