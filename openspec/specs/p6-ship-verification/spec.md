## Purpose

P6.5 ship verification — pytest coverage for P6 ship criteria, `scripts/test_p6_smoke.py`, and `docs/context.md` stamp only after green.

## Requirements

### Requirement: P6 pytest coverage for ship criteria
The project MUST provide (or retain) automated tests covering step 6.5 ship criteria, filling gaps where prior steps left them incomplete:

- `tests/travel_engine/` — route optimizer polyline alignment (`leg_polylines` / `day_polyline`) and None-on-fallback degradation
- `tests/trips/` — `save_from_state` UoW + polyline persist, ownership 403, claim 200/403/409, GeoJSON LineString when polylines present
- `tests/planner/` — generate 409 floor, single terminal-event regression, disconnect cancel, cache hit still persists a **new** `trip_id` without `tool_started`/`tool_done`
- `tests/core/` — Redis limiter/cache selection + fail-open (mocked Redis)

Existing tests that already assert these behaviors MUST NOT be duplicated without cause; missing scenarios MUST be added in this change.

#### Scenario: Cache-hit persistence is covered by pytest
- **WHEN** the planner cache-hit tests run
- **THEN** they assert a second generate yields `itinerary_done` with a distinct `trip_id` and no tool-loop events

#### Scenario: Single terminal frame regression exists
- **WHEN** a mocked generate emits `itinerary_done` plus a spurious extra terminal
- **THEN** the client-facing stream assertion allows exactly one terminal frame

### Requirement: P6 smoke script
The project MUST provide `scripts/test_p6_smoke.py` that exercises:

1. destinations search + readiness + places page sanity
2. `POST /api/v1/planner/generate` SSE — live `tool_started`/`tool_done` then exactly one `itinerary_done` with `trip_id`
3. `GET /trips/{id}/geojson` — at least one LineString when geometry available
4. second identical generate — fast cache path, **new** `trip_id`, no `tool_started`
5. `POST /trips/{id}/claim` after login → 200, then re-claim → 409
6. import guards (no redis in planner/trips routers; no `StreamingResponse` in `planner/service.py`; litellm only via `core/llm/client.py`)

Smoke MUST exit non-zero on any failed section. Live OSRM may be optional; in-memory cache is sufficient for section 4 when `REDIS_URL` is empty.

#### Scenario: Smoke fails closed
- **WHEN** any smoke section fails
- **THEN** the script exits non-zero and P6 MUST NOT be marked complete in `docs/context.md`

### Requirement: Context stamp only after green
After `pytest tests/ -v` and `scripts/test_p6_smoke.py` succeed, `docs/context.md` MUST be updated to: Progress **6.0–6.5** ✅, Next → **P7.1**, implemented modules for cache backends + Redis limiter, live endpoints confirmed, deployment reverse-proxy note and frontend `fetch()` SSE note present, planner/trips HTTP stubs cleared, P7 edit ops remaining stubs. The update MUST NOT claim P7 complete.

#### Scenario: Premature stamp forbidden
- **WHEN** pytest or smoke has not passed in the apply session
- **THEN** agents MUST NOT mark P6 complete in `docs/context.md`
