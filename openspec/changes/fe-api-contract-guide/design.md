## Context

`docs/FE_guide.md` already locks the sibling Next.js stack, cookie/CORS Option A, envelope parsing, domain route list, and a thin SSE overview (from completed change `frontend-stack-guide`). Frontend implementers still cannot build typed `lib/api/*` clients without reading Python: request bodies, response DTOs, auth per route, error codes, pagination shape, GeoJSON properties, and SSE `data` payloads are missing or only referenced by name. One readiness UX line in the guide also implies a returned `search_available` field that `DestinationReadinessOut` does not expose.

Stakeholders: FE repo authors / agents; backend remains source of truth via `src/*/schemas.py` and live routers.

## Goals / Non-Goals

**Goals:**

- Expand `docs/FE_guide.md` into a FE-facing **API navigation contract** sufficient to implement typed clients, Zod schemas, Query hooks, SSE progress UI, and MapLibre rendering without inventing fields.
- Keep one canonical guide file (stack + API) so the sibling repo has a single pointer.
- Ground every table in live code; prefer short TypeScript-shaped sketches over prose.
- Correct readiness UX guidance to match `DestinationReadinessOut`.

**Non-Goals:**

- Changing FastAPI routes, schemas, cookies, or OAuth callback behavior.
- Scaffolding the Next.js app or committing OpenAPI codegen artifacts.
- Duplicating full `docs/app/system.md` / LLD into the FE guide.
- Documenting evaluation HTTP (stub) as if it were callable.
- Auto-syncing the guide from OpenAPI on every backend change (manual update rule remains).

## Decisions

### D1 — Expand `FE_guide.md`, do not split a second “API.md”

- **Choice:** Add numbered sections inside `docs/FE_guide.md` (auth matrix, DTOs, errors, SSE payloads, GeoJSON, rate limits, source-of-truth). Keep stack sections 1–13; insert or append contract sections without rewriting locked stack tables.
- **Why:** One canonical FE contract; avoids drift between “stack guide” and “API guide.”
- **Alternatives:** New `docs/FE_api.md` — rejected for MVP (two files to keep in sync).

### D2 — Auth matrix mirrors `docs/context.md` Live endpoints

- **Choice:** Every listed route gets Method / Path / Auth / Notes. Auth vocabulary: `None`, `Optional`, `Required`, plus ownership notes (guest session vs owner) where trips differ.
- **Why:** FE currently has paths without knowing which calls 401; context.md already has the matrix — guide must carry it for FE readers who may not open context.
- **Alternatives:** “See context.md only” — rejected; FE team’s primary doc is FE_guide.

### D3 — DTO sketches as TypeScript interfaces, sourced from Pydantic

- **Choice:** Document compact `type`/`interface` sketches for: `AuthMeResponse`, `UserOut`, `DestinationOut`, `DestinationReadinessOut`, `PlaceOut`, `PlanRequest`, `TripOut`, `TripPlaceOut`, `ReorderStopsIn`, `AddStopIn`, envelopes (`ApiResponse`, `ErrorResponse`, `PaginatedResponse` + `page`/`size` query defaults).
- **Why:** FE builds Zod from these; naming can match backend field names exactly.
- **Rule:** Mark sketches as **illustrative mirrors** of `src/*/schemas.py`; if conflict, Python + OpenAPI `/docs` win.
- **Alternatives:** Full OpenAPI dump in markdown — too large / stale; link-only with no fields — insufficient for offline FE planning.

### D4 — Envelope nuance: GeoJSON and SSE are exceptions

- **Choice:** Explicitly call out:
  - Most JSON → `ApiResponse[T]` or list pagination via `PaginatedResponse[T]` (places list; trips list may wrap items — document actual router return).
  - `GET /trips/{id}/geojson` → raw GeoJSON `FeatureCollection` (not `ApiResponse`).
  - `POST /planner/generate` → SSE frames (not `ApiResponse`).
- **Why:** FE client must branch parsers; current guide only calls out SSE exception.

### D5 — SSE catalog: event names + representative data, not full itinerary schema dump

- **Choice:** Table of progress events (`preferences_done`, `phase_changed`, `tool_done`, `tool_batch_done`, …) and terminal (`itinerary_done`, `error`, `clarification_needed`) with example `data` keys. Note `itinerary_done` may be enriched with `trip_id` after save. Note cache replay skips tool events.
- **Why:** Progress UI needs keys; dumping full itinerary nested graph is brittle and belongs in trip GET after redirect.
- **Alternatives:** Require FE to parse full itinerary from SSE only — discouraged; prefer navigate to trip by `trip_id`.

### D6 — GeoJSON map contract for MapLibre

- **Choice:** Document Feature types:
  - Point: `[lng, lat]`, properties `name`, `day`, `order`, `suggested_start_time`, `place_id`, `trip_place_id`
  - LineString: concatenated day legs when polylines exist; properties `day`, `trip_id`
- **Why:** Matches `TripService.build_geojson`; FE should not invent property names.

### D7 — Error / rate-limit codes for UX branching

- **Choice:** Catalog FE-relevant HTTP error `code` values from global handler + domain (`destination_not_ready` 409, `not_found`, `unauthorized`, `forbidden`, `rate_limit_exceeded`, `validation_error`, `internal_error`, …) plus SSE terminal `error` codes (`generation_timeout`, `graph_recursion_limit`).
- **Why:** Sonner / screen branching needs stable codes, not only HTTP status.
- **Also:** Note UX-visible limits (destination search IP limit; planner generate limit; trip edit dependency limit) at a summary level — point to middleware/config for exact numbers, avoid inventing if config-driven.

### D8 — Source of truth hierarchy

```
1. Live routers + src/*/schemas.py     (canonical)
2. http://localhost:8000/docs          (machine-readable companion)
3. docs/context.md Live endpoints      (auth matrix checkpoint)
4. docs/FE_guide.md                    (FE-oriented mirror — update when routes/DTOs change)
```

- **Choice:** Guide states this hierarchy and a maintenance rule: when Live endpoints or public schemas change, update FE_guide contract sections in the same session/PR as the API change (or immediately after).
- **Alternatives:** Codegen committed OpenAPI into FE repo — deferred.

### D9 — Fix readiness UX inaccuracy

- **Choice:** Screen-flow / readiness section MUST use returned fields: `tier`, `score`, `place_count`, `enriched_pct`, `indexed_pct`, `message`. MUST NOT claim `search_available` is in the JSON (it is an internal input to scoring; `indexed_pct` already reflects Qdrant availability).
- **Why:** Prevents FE from waiting on a nonexistent field.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Guide DTOs drift from Python | Hierarchy + “schemas win”; keep sketches short; update with API PRs |
| SSE payloads evolve / are incomplete | Document representative keys; FE treats unknown events as ignore-or-log; prefer trip GET after `trip_id` |
| Auth matrix duplicated vs context.md | Same vocabulary; optional one-line cross-link both ways |
| Guide becomes huge | Tables over prose; no architecture essays; no stub evaluation APIs |
| Trips list pagination vs ApiResponse wrapping details | Verify against `trips/router.py` when writing the guide section; document exact shape |

## Migration Plan

1. Apply change: edit `docs/FE_guide.md` only (plus optional context pointer).
2. No runtime deploy; FE consumers pull updated guide.
3. Rollback: revert doc commit.

## Open Questions

- How much of itinerary nested object inside `itinerary_done` to sketch — default: minimal (`trip_id` + advise GET trip); expand only if FE needs interim render before navigation.
- Exact numeric rate-limit values are config-driven — document “which routes” + point to settings/middleware; only hard-code numbers already published in `docs/context.md` (e.g. destinations/search 20/min/IP) when writing the guide.

**Resolved at design time:** `GET /trips` and `GET /places` return bare `PaginatedResponse[T]` (not wrapped in `ApiResponse`). Destination search returns `ApiResponse[list[DestinationOut]]`.
