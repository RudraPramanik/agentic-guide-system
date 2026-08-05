"""Planner HTTP router — POST /generate SSE adapter over PlannerService (P6.2)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.router import COOKIE_SESSION, SESSION_MAX_AGE_SECONDS, _cookie_secure
from src.config import get_settings
from src.core.database.session import get_db
from src.core.security.jwt import TokenPayload
from src.core.security.permissions import optional_auth
from src.destinations.exceptions import DestinationNotReadyError
from src.destinations.service import DestinationService
from src.planner.cache import _replay_cached, maybe_get_cached_state
from src.planner.schemas import PlanRequest
from src.planner.service import PlannerService
from src.trips.service import TripService

router = APIRouter(prefix="/api/v1/planner", tags=["planner"])

TERMINAL_EVENTS = frozenset({"itinerary_done", "error", "clarification_needed"})

_QUEUE_POLL_TIMEOUT_SECONDS = 1.0


def sse_frame(event: str, data: dict[str, Any]) -> str:
    """Format one SSE frame (not ApiResponse)."""
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/generate")
async def generate_plan(
    body: PlanRequest,
    request: Request,
    payload: TokenPayload | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream planner progress as SSE. Buffers terminal events, saves trip on
    itinerary_done, yields exactly one enriched terminal frame.
    """
    session_id = request.cookies.get(COOKIE_SESSION) or str(uuid.uuid4())

    dest = await DestinationService(db).get_by_id(body.destination_id)

    settings = get_settings()
    if dest.place_count < settings.PLANNER_ABSOLUTE_MIN_PLACES:
        raise DestinationNotReadyError(place_count=dest.place_count)

    # Floor passed — cache lookup may run (P6.2 always misses)
    base_lat = body.base_lat if body.base_lat is not None else float(dest.lat)
    base_lng = body.base_lng if body.base_lng is not None else float(dest.lng)
    user_id: UUID | None = payload.user_id if payload else None

    async def event_gen():
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

        def on_event(event: str, data: dict) -> None:
            queue.put_nowait((event, data))

        cached_state = await maybe_get_cached_state(body, base_lat, base_lng)

        if cached_state is not None:
            task = asyncio.create_task(_replay_cached(cached_state, on_event))
        else:
            task = asyncio.create_task(
                PlannerService().generate(
                    destination_id=body.destination_id,
                    raw_input=body.raw_input,
                    base_lat=base_lat,
                    base_lng=base_lng,
                    session_id=session_id,
                    on_event=on_event,
                )
            )

        pending_terminal: tuple[str, dict[str, Any]] | None = None
        try:
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    break
                try:
                    event, data = await asyncio.wait_for(
                        queue.get(),
                        timeout=_QUEUE_POLL_TIMEOUT_SECONDS,
                    )
                except TimeoutError:
                    if task.done() and queue.empty():
                        break
                    continue
                if event in TERMINAL_EVENTS:
                    pending_terminal = (event, data)
                    continue
                yield sse_frame(event, data)

            if pending_terminal:
                event, data = pending_terminal
                if event == "itinerary_done":
                    try:
                        final_state = task.result()
                    except Exception:
                        final_state = None
                    if final_state is not None:
                        trip = await TripService(db).save_from_state(
                            final_state,
                            user_id=user_id,
                            session_id=session_id,
                        )
                        if trip is not None:
                            data = {**data, "trip_id": str(trip.id)}
                        if body.accommodation_label:
                            data = {
                                **data,
                                "accommodation_label": body.accommodation_label,
                            }
                yield sse_frame(event, data)
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

    response = StreamingResponse(event_gen(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    # Align with auth router (httponly=True) — intentional hardening vs step6 snippet
    response.set_cookie(
        COOKIE_SESSION,
        session_id,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return response
