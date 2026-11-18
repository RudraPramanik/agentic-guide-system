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

from src.auth.router import (
    COOKIE_SESSION,
    SESSION_MAX_AGE_SECONDS,
    _cookie_samesite,
    _cookie_secure,
)
from src.config import get_settings
from src.core.database.session import get_db
from src.core.responses import ApiResponse
from src.core.security.jwt import TokenPayload
from src.core.security.permissions import optional_auth
from src.core.observability.tracing import (
    end_generation_trace,
    start_generation_trace,
)
from src.destinations.exceptions import DestinationNotReadyError
from src.destinations.service import DestinationService
from src.planner.cache import (
    _replay_cached,
    maybe_get_cached_state,
    maybe_set_cached_state,
)
from src.planner.location import build_generate_location
from src.planner.runs.identity import resolve_idempotency_key
from src.planner.runs.models import TERMINAL_RUN_STATUSES, RunStatus
from src.planner.runs.outcomes import map_generate_outcome
from src.planner.runs.service import PlannerRunService
from src.planner.schemas import PlanRequest, PlannerRunOut, location_key_suffix
from src.planner.service import PlannerService
from src.trips.service import TripService

router = APIRouter(prefix="/api/v1/planner", tags=["planner"])

TERMINAL_EVENTS = frozenset({"itinerary_done", "error", "clarification_needed"})

_QUEUE_POLL_TIMEOUT_SECONDS = 1.0


def sse_frame(event: str, data: dict[str, Any]) -> str:
    """Format one SSE frame (not ApiResponse)."""
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _with_run_id(data: dict[str, Any], run_id: UUID | None) -> dict[str, Any]:
    if run_id is None:
        return data
    return {**data, "run_id": str(run_id)}


def _coerce_status(status: RunStatus | str) -> RunStatus:
    if isinstance(status, RunStatus):
        return status
    return RunStatus(str(status))


def _existing_run_frame(
    status: RunStatus | str,
    trip_id: UUID | None,
    failure_code: str | None,
) -> tuple[str, dict[str, Any]]:
    current = _coerce_status(status)
    if current not in TERMINAL_RUN_STATUSES:
        return "error", {"code": "run_in_progress"}
    if trip_id is not None:
        return "itinerary_done", {"trip_id": str(trip_id)}
    return "error", {"code": failure_code or "generation_aborted"}


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

    base_lat = body.base_lat if body.base_lat is not None else float(dest.lat)
    base_lng = body.base_lng if body.base_lng is not None else float(dest.lng)
    user_id: UUID | None = payload.user_id if payload else None

    discovery_anchor: dict[str, Any] | None = None
    search_area: dict[str, Any] | None = None
    loc_suffix = ""
    if settings.LOCATION_V2_ENABLED:
        discovery_anchor, search_area = await build_generate_location(body, dest, db)
        if body.discovery_anchor is not None or body.radius_km is not None:
            loc_suffix = location_key_suffix(body)
    reasoning_suffix = "reasoning-v1" if settings.REASONING_LAYER_ENABLED else ""

    async def event_gen():
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        run_id_value: UUID | None = None
        task: asyncio.Task | None = None
        disconnected = False
        from_cache = False

        def on_event(event: str, data: dict) -> None:
            queue.put_nowait((event, data))

        try:
            if settings.RUN_TRACKING_ENABLED:
                idem_key, input_hash = resolve_idempotency_key(
                    request.headers.get("idempotency-key"),
                    body,
                    base_lat,
                    base_lng,
                    session_id,
                    location_suffix=loc_suffix,
                )
                run, created = await PlannerRunService(db).resolve(
                    session_id=session_id,
                    user_id=user_id,
                    idempotency_key=idem_key,
                    input_hash=input_hash,
                )
                run_id_value = run.id
                if not created:
                    event, data = _existing_run_frame(
                        run.status,
                        run.trip_id,
                        run.failure_code,
                    )
                    yield sse_frame(event, _with_run_id(data, run_id_value))
                    return

            cached_state = await maybe_get_cached_state(
                body,
                base_lat,
                base_lng,
                location_suffix=loc_suffix,
                reasoning_suffix=reasoning_suffix,
            )
            from_cache = cached_state is not None

            if from_cache:

                async def _run_cached() -> dict[str, Any]:
                    start_generation_trace(
                        name="planner.generate.cache_hit",
                        session_id=session_id,
                        user_id=str(user_id) if user_id is not None else None,
                        metadata={
                            "destination_id": str(body.destination_id),
                            "from_cache": True,
                        },
                    )
                    try:
                        return await _replay_cached(cached_state, on_event)
                    finally:
                        end_generation_trace(
                            outcome="cache_hit",
                            metadata={
                                "destination_id": str(body.destination_id),
                                "session_id": session_id,
                                "from_cache": True,
                            },
                        )

                task = asyncio.create_task(_run_cached())
            else:
                task = asyncio.create_task(
                    PlannerService().generate(
                        destination_id=body.destination_id,
                        raw_input=body.raw_input,
                        base_lat=base_lat,
                        base_lng=base_lng,
                        session_id=session_id,
                        on_event=on_event,
                        user_id=user_id,
                        discovery_anchor=discovery_anchor,
                        search_area=search_area,
                        days=body.days,
                    )
                )

            pending_terminal: tuple[str, dict[str, Any]] | None = None
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    disconnected = True
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
                yield sse_frame(event, _with_run_id(data, run_id_value))

            if disconnected and run_id_value is not None:
                return

            task_error: BaseException | None = None
            state: dict[str, Any] | None = None
            if task.done() and not task.cancelled():
                try:
                    result = task.result()
                except Exception as exc:
                    task_error = exc
                else:
                    state = result if isinstance(result, dict) else None

            if pending_terminal:
                event, data = pending_terminal
                if event == "itinerary_done":
                    trip = None
                    if state is not None:
                        trip = await TripService(db).save_from_state(
                            state,
                            user_id=user_id,
                            session_id=session_id,
                            run_id=run_id_value,
                        )
                        if trip is not None:
                            data = {**data, "trip_id": str(trip.id)}
                        if body.accommodation_label:
                            data = {
                                **data,
                                "accommodation_label": body.accommodation_label,
                            }
                        if not from_cache:
                            await maybe_set_cached_state(
                                body,
                                base_lat,
                                base_lng,
                                state,
                                location_suffix=loc_suffix,
                                reasoning_suffix=reasoning_suffix,
                            )
                    if trip is None and run_id_value is not None:
                        await PlannerRunService(db).finish_open(
                            run_id_value,
                            RunStatus.FAILED,
                            "generation_aborted",
                        )
                elif run_id_value is not None:
                    outcome = map_generate_outcome(
                        disconnected=False,
                        task_error=task_error,
                        state=state,
                        terminal_event=event,
                        terminal_data=data,
                        saved=False,
                    )
                    await PlannerRunService(db).finish_open(
                        run_id_value,
                        outcome.status,
                        outcome.failure_code,
                    )
                yield sse_frame(event, _with_run_id(data, run_id_value))
            elif task.done() and not task.cancelled():
                if run_id_value is not None:
                    outcome = map_generate_outcome(
                        disconnected=False,
                        task_error=task_error,
                        state=state,
                        terminal_event=None,
                        terminal_data=None,
                        saved=False,
                    )
                    await PlannerRunService(db).finish_open(
                        run_id_value,
                        outcome.status,
                        outcome.failure_code,
                    )
                yield sse_frame(
                    "error",
                    _with_run_id({"code": "missing_terminal"}, run_id_value),
                )
        finally:
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            if disconnected and run_id_value is not None:
                await PlannerRunService(db).finish_open(
                    run_id_value,
                    RunStatus.CANCELLED,
                    "client_disconnect",
                )

    response = StreamingResponse(event_gen(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    # Align with auth router (httponly=True) — intentional hardening vs step6 snippet
    response.set_cookie(
        COOKIE_SESSION,
        session_id,
        httponly=True,
        samesite=_cookie_samesite(),
        secure=_cookie_secure(),
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return response


@router.get("/runs/{run_id}")
async def get_planner_run(
    run_id: UUID,
    request: Request,
    payload: TokenPayload | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PlannerRunOut]:
    """Owner read of one planner run. Missing is 404. Wrong owner is 403."""
    run = await PlannerRunService(db).get_for_access(
        run_id,
        user_id=payload.user_id if payload else None,
        session_id=request.cookies.get(COOKIE_SESSION),
    )
    status = run.status.value if isinstance(run.status, RunStatus) else str(run.status)
    return ApiResponse(
        data=PlannerRunOut(
            run_id=run.id,
            status=status,
            failure_code=run.failure_code,
            trip_id=run.trip_id,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
    )
