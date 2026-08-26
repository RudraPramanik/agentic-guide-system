"""Place service — list/get with mandatory destination existence check; LLM enrichment."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import WandrLLMError
from src.core.llm.client import chat_completion  # module-scope — patchable in tests
from src.core.pagination import PageParams
from src.destinations.exceptions import DestinationNotFoundError
from src.destinations.repository import DestinationRepository
from src.places.constants import PLACE_TAG_VOCAB
from src.places.models import Place
from src.places.repository import PlaceRepository
from src.places.schemas import PlaceOut

log = structlog.get_logger()


@dataclass(frozen=True)
class ParsedEnrichment:
    summary: str
    tags: list[str]


class PlaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PlaceRepository(session)
        self.dest_repo = DestinationRepository(session)

    async def list_by_destination(
        self, destination_id: uuid.UUID, params: PageParams
    ) -> tuple[list[PlaceOut], int]:
        """
        LOCKED (v2): destination existence check is MANDATORY, not optional.
        1. Verify destination exists — raises DestinationNotFoundError (404)
        2. places, total = await self.repo.list_by_destination(...)
        3. return [PlaceOut.from_place(p) for p in places], total
        """
        dest = await self.dest_repo.get_by_id(destination_id)
        if dest is None:
            raise DestinationNotFoundError(destination_id=str(destination_id))

        places, total = await self.repo.list_by_destination(destination_id, params)
        return [PlaceOut.from_place(p) for p in places], total

    async def get_by_id(self, place_id: uuid.UUID) -> PlaceOut:
        """get_by_id_or_raise on Place repo → PlaceOut.from_place."""
        place = await self.repo.get_by_id_or_raise(place_id)
        return PlaceOut.from_place(place)

    async def _call_llm_and_parse(self, place: Place) -> ParsedEnrichment | None:
        """
        LLM call + JSON parse + vocab filtering ONLY. No DB read/write. This split exists
        so the batch script (3.5) can run this concurrently across many places while
        keeping the actual DB write serialized on one session.
        """
        prompt = [
            {
                "role": "user",
                "content": (
                    f"Place name: {place.name}\nCategory: {place.category}\n"
                    f"Raw tags: {place.tags}\n\n"
                    "Return a JSON object with exactly two keys: "
                    '"summary" (1-3 sentence description) and '
                    f'"tags" (a list of zero or more values from this exact vocabulary: {PLACE_TAG_VOCAB}).'
                ),
            }
        ]
        try:
            result = await chat_completion(
                messages=prompt, response_format={"type": "json_object"}
            )
            raw = result.content if hasattr(result, "content") else result
        except WandrLLMError as e:
            log.warning("enrichment.llm_failed", place_id=str(place.id), error=str(e))
            return None

        try:
            data = json.loads(raw)
            summary = str(data["summary"]).strip()
            if not summary:
                raise ValueError("empty summary")
            raw_tags = data.get("tags", [])
            if not isinstance(raw_tags, list):
                raise TypeError("tags must be a list")
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            log.warning(
                "enrichment.malformed_response", place_id=str(place.id), error=str(e)
            )
            return None

        filtered_tags = [t for t in raw_tags if t in PLACE_TAG_VOCAB]
        return ParsedEnrichment(summary=summary, tags=filtered_tags)

    async def enrich_place(self, place: Place) -> tuple[str, list[str]] | None:
        """
        Re-runnable: places with summary already set are skipped (LLM not called).
        Persists to place.summary and place.enriched_tags ONLY — place.tags (raw OSM
        dict) is never touched. Flush-only; caller commits.
        """
        if place.summary is not None:
            return None
        parsed = await self._call_llm_and_parse(place)
        if parsed is None:
            return None
        await self.repo.update(
            place.id,
            {
                "summary": parsed.summary,
                "enriched_tags": parsed.tags,
            },
        )
        return parsed.summary, parsed.tags
