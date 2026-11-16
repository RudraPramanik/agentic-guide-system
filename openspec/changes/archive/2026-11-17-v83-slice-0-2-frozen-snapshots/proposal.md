## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9, subslice **0.2**) is the next step after the archived 0.1 audit. Guard G8 says later slices must not change existing paths, envelopes, SSE event names, or GeoJSON shape. Domain tests exist, and `tests/snapshots/` does not. There is no `docs/steps/step*.md` for this work; the task id is blueprint row 0.2. `docs/context.md` still describes post-P7 / v7 and is not the task list for this subslice.

## What Changes

- Add request and response fixtures plus pytest comparisons under `tests/snapshots/**` and `tests/fixtures/**`.
- Freeze the surfaces named in row 0.2: destination search, readiness, the planner SSE event sequence (including the pre-stream 409), trip CRUD, GeoJSON, day edits, and guest versus authenticated access.
- Compare normalized bodies. UUIDs, timestamps, and session cookie values are placeholders. Status codes, envelope keys, SSE event names and order, and GeoJSON geometry types stay exact.
- No production behavior changes. No **BREAKING** changes.

The apply step starts by running the existing suite. If that suite is already red, the subslice stops and reports. It does not repair unrelated failures.

## Capabilities

### New Capabilities

- `legacy-api-snapshots`: a snapshot suite that locks today's HTTP, SSE, and GeoJSON contract and does not call live geocoding, Overpass, OSRM, the LLM, or Qdrant.

### Modified Capabilities

(none — destinations, readiness, planner SSE, trips CRUD, and day-edit requirements stay as they are. This change adds a regression lock. It does not change those contracts.)

## Impact

- **Work surface:** guideagent tests only. `docs/v8.2/repository_audit.md` and `docs/FE_guide.md` are read as evidence.
- **Files written:** `tests/snapshots/**` and `tests/fixtures/**` only.
- **Reused, not edited:** `tests/conftest.py` (Postgres `wandr_test`, ASGI client, JWT helpers). Qdrant and embedding startup stay mocked there.
- **No impact on:** application code, migrations, settings, dependencies, HTTP paths, DTO shapes, SSE event names, Docker, or `docs/context.md`.
- **Downstream:** subslices 0.3–0.5 and Slices 1–9 cite this suite when they claim the legacy contract is unchanged.

## Non-goals

- No baseline metrics (0.3), `[SET IN S0]` fill-in or ADR-001–ADR-004 (0.4), or architecture tests (0.5).
- No `GET /destinations/resolve` and no `POST /destinations/{id}/prepare`. Resolve always calls Nominatim, including on a database hit. Prepare calls Overpass. Row 0.2 names destination search, not those two.
- No live planner graph, no recorded LLM fixtures (that is 2.2), and no golden-set metrics (that is 0.3).
- No frontend edits and no edits to `docs/FE_guide.md`, `docs/context.md`, or the blueprint.
- No new package. `syrupy` and similar snapshot libraries are out. `requirements.txt` is outside the allowed paths.
- No repair of a red existing suite, and no change to production modules so a snapshot is easier to write.

## Constraints

From `AGENT.md` and the v8.3 invariants, this subslice must:

- Stay inside `tests/snapshots/**` and `tests/fixtures/**`. Any other write is a stop.
- Not call Nominatim, Overpass, OSRM, or an LLM. Search snapshots use a seeded database hit so `DestinationService.search` returns before `geocode`. SSE snapshots patch `PlannerService.generate` the way `tests/planner/test_generate_sse.py` already does. Day-edit snapshots inject `FakeRoutingProvider` the way `tests/trips/test_trip_edit_http.py` already does. Readiness uses the in-process `is_qdrant_available()` flag, which stays false while the test client's Qdrant ensure is mocked. It does not open a Qdrant socket.
- Leave `travel_engine/` untouched. The snapshot imports the existing fake routing provider. It does not add I/O there.
- Preserve the envelopes that already exist: `ApiResponse` for search, readiness, trip get, claim, and day edits; bare `PaginatedResponse` for trip list; raw GeoJSON for `/geojson`; SSE frames for generate; `ErrorResponse` for 401, 403, and 409. Do not wrap GeoJSON or SSE in `ApiResponse`.
- Not add a dependency. A new package would need `requirements.txt`, which this subslice cannot edit.
- Not update `docs/context.md`. The OpenSpec repo rule asks for that update when a build step completes. Row 0.2's allowed paths forbid it, the same way subslice 0.1 left that file alone. The snapshot suite is the record.

§18 item 2 applies here: an already-red suite halts the subslice. The audit's contradiction about `tool_started` and `validation_done` stays closed. Snapshots lock the names the code emits (`preferences_done`, `phase_changed`, `tool_done`, `tool_batch_done`, and one of `itinerary_done`, `error`, `clarification_needed`). They do not add the two names that have no emitter.
