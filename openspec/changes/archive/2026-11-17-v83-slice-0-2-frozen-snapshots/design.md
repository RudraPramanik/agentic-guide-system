## Context

See proposal.md — Why. Subslice 0.1 is archived. `docs/v8.2/repository_audit.md` records the live SSE names, the 409 floor, GeoJSON property names, and the fact that `tool_started` and `validation_done` have no emitter. `tests/conftest.py` already provides the `wandr_test` engine, the ASGI `client`, and JWT helpers, and it mocks Qdrant collection ensure plus embedding load. There is no `tests/snapshots/` tree. `requirements.txt` has pytest, pytest-asyncio, and pytest-mock, and no snapshot plugin.

This change adds no external I/O. It does not add a timeout, a retry, or a provider fallback. The guard is the opposite: a snapshot that reaches Nominatim, Overpass, OSRM, the LLM gateway, or Qdrant fails. `travel_engine/` stays pure. Day-edit cases inject the existing `FakeRoutingProvider` from the test, the same way `tests/trips/test_trip_edit_http.py` does.

## Goals / Non-Goals

**Goals:**

- One command, `pytest tests/snapshots -v`, fails on contract drift and passes without live providers.
- Fixtures are reviewed files, not a library's hidden store.
- The router framing is what is locked: envelopes, status codes, SSE event names on the wire, GeoJSON geometry types.

**Non-Goals:**

- Proving the live LangGraph node list still calls each progress event. That needs the replay layer in subslice 2.2. This suite stubs the planner.
- Editing `tests/conftest.py`, production code, or `requirements.txt`.

## Decisions

### 1. Checked-in JSON, compared in pytest

Store expected bodies in `tests/fixtures/snapshots/*.json`. Tests build the request, call the ASGI client, normalize the response, and assert equality. No `--update` switch. Changing a fixture is a diff in the pull request.

Alternative considered: `syrupy` or a similar plugin. Rejected. `AGENT.md` forbids a new package without a `requirements.txt` why-comment, and row 0.2 cannot edit that file.

Alternative considered: assert a few keys inline and skip fixture files. Rejected. Row 0.2 asks for request/response fixtures, and G8 needs a diff when a key appears or disappears.

### 2. Normalize identifiers, keep the contract exact

Before compare, walk the JSON and replace UUID strings, ISO datetimes, and `wandr_session` values with placeholders (`<uuid>`, `<datetime>`, `<session>`). Do this in one helper under `tests/snapshots/`. Leave numbers that are not identifiers (lat, lng, `place_count`, `score`, `days`, `order`) exact. Seed those from constants, not from `uuid4`, so two runs produce the same coordinates and counts.

SSE is not JSON. Parse frames into an ordered list of `{event, data}` and normalize `data` the same way. The fixture stores that list.

Alternative considered: byte-compare raw bodies. Rejected. Primary keys and timestamps change every test, so the suite would be red on a clean run.

### 3. Reuse the parent ASGI client

Snapshot tests use the `client` and `db_session` fixtures from `tests/conftest.py`. They do not copy the engine setup and they do not edit that file. "No live network" means no provider HTTP. Postgres `wandr_test` stays, because that is how the existing suite already reaches the routers. A machine without that database cannot go green; that is the same precondition as `pytest tests/trips`.

Alternative considered: call Pydantic models in-process and skip HTTP. Rejected. G8 is about the wire: paths, envelopes, event names, GeoJSON shape. An in-process model test would miss a router that wraps GeoJSON in `ApiResponse`.

### 4. Provider calls fail closed inside this package

`tests/snapshots/conftest.py` (allowed, because it sits under `tests/snapshots/**`) autouses patches:

- `src.geo.geocoder.geocode` and `src.geo.geocoder.geocode_search` raise if called.
- `src.core.llm.client.chat_completion` and `chat_with_tools` raise if called.
- `src.destinations.service.is_qdrant_available` returns `False`.

Do not patch `httpx.AsyncClient`. The ASGI test client is httpx, and a blanket patch would break the harness. Search cases seed a destination whose name matches `q`, so `DestinationService.search` returns on the database hit and never reaches `geocode`. Readiness cases never flip the Qdrant flag. Generate cases patch `PlannerService.generate` and do not compile the graph. GeoJSON reads persisted polylines only. Day edits construct `TripService` with `FakeRoutingProvider` via the same router patch the edit HTTP tests use.

`_qdrant_available` defaults to false, and the parent client already mocks `ensure_places_collection`. The explicit patch is there so a test that ran real ensure earlier in the same process cannot flip readiness.

### 5. What each fixture locks

| Fixture | Request | Frozen result |
|---|---|---|
| Search | `GET /api/v1/destinations/search?q=` for a seeded name | 200 `ApiResponse`; `data[]` keys of today's destination item |
| Readiness | `GET /api/v1/destinations/{id}/readiness` with seeded counters and search unavailable | 200 `ApiResponse`; `tier` and `message` from the pure scorer |
| SSE progress | `POST /api/v1/planner/generate` for a destination at the floor; stub emits `preferences_done`, `phase_changed`, `tool_done`, `tool_batch_done`, then `itinerary_done` | 200; that event order; one terminal; `cache-control: no-cache`; `x-accel-buffering: no` |
| SSE terminals | separate stubs for a lone `error` and a lone `clarification_needed` | each name once, and no second terminal |
| SSE double terminal | stub emits `itinerary_done` then `error` | exactly one terminal on the wire. The router keeps the last terminal, so the fixture is `error` |
| Floor | destination with `place_count` 0 | 409 `destination_not_ready`; body has no `event:` line; generate stub is not called |
| Trip list | `GET /api/v1/trips` with no credentials | 401 error envelope |
| Guest get | matching `wandr_session` | 200 `ApiResponse` |
| Guest mismatch | other session | 403, not 404 |
| Delete | no credentials | 401 |
| Claim | authenticated caller, matching session, unclaimed trip | 200 `ApiResponse` |
| GeoJSON points | stops with null polylines | raw `FeatureCollection`; Point only; properties `name`, `day`, `order`, `suggested_start_time`, `place_id`, `trip_place_id` |
| GeoJSON line | one decodable polyline | a LineString whose properties include `day` and `trip_id`; coordinates `[lng, lat]` |
| Day edits | owner calls reorder, remove, add, reoptimize | each 200 `ApiResponse` |
| Anonymous edits | the four edit routes with no credentials | each 401 |

`preferences_done` is a real progress name in the audit. The progress fixture includes it when the stub emits it, beside `phase_changed`. The stub list is the audit's emitted progress names that a single scripted run can show together: `preferences_done`, `phase_changed`, `tool_done`, `tool_batch_done`, then `itinerary_done`. `tool_started` and `validation_done` stay out.

Trip bodies are large. Freeze the normalized `TripOut` key set and, for reorder, the stop order. Do not freeze narrative prose. Generate does not persist a model-written itinerary; the stub returns a small schedule the router can frame.

### 6. Requests that need an id

Query strings and edit bodies that are stable live as JSON under `tests/fixtures/snapshots/requests/`. The test substitutes the seeded destination id, trip id, or place id, then normalizes the response before compare. The committed response fixture already uses placeholders, so the substitution does not appear in the expected file.

### 7. Red suite stops the subslice

The first apply task runs the existing suite, excluding `tests/snapshots`, before any fixture is written. A failure stops the work and is reported. Allowed paths do not include the failing test or the production fix. This design does not choose which older failure to patch.

## Risks / Trade-offs

- [The stubbed SSE sequence stays green after the graph stops emitting an event] → Accepted for 0.2. The suite locks router framing and the names on the wire for a known script. Subslice 2.2 locks live model output. The risk is recorded so nobody treats this suite as proof of the graph.
- [Process-global Qdrant flag leaks from another test] → The snapshot package forces `is_qdrant_available` false for its tests.
- [A search query misses the seed and calls Nominatim] → The geocode patch raises, and the seed name is the query. The failure is local and loud.
- [Normalizer hides a real id-field rename] → Placeholders keep the key. Renaming `place_id` to another key fails the key set. Replacing a non-id number is out of the normalizer.
- [Existing suite is already red] → Halt. Do not "fix forward" inside this change.
- [Readers treat the fixture as permission to change production code] → Rollback is deleting `tests/snapshots/` and `tests/fixtures/snapshots/`. Production files are not part of the diff.

## Migration Plan

No schema, flag, or deploy step. The suite runs in the existing pytest job because `testpaths` already includes `tests`.

Rollback: delete `tests/snapshots/` and `tests/fixtures/snapshots/`. Nothing else was added.

## Open Questions

None. Fixture filenames may vary as long as they stay under `tests/fixtures/snapshots/` and each row in Decision 5 has a file.
