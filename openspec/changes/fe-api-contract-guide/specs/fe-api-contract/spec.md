## ADDED Requirements

### Requirement: FE API contract lives in the canonical frontend guide

The project SHALL expand `docs/FE_guide.md` so it doubles as the FE-facing API navigation contract for the sibling Next.js app, without creating a second competing API guide file. Stack lock sections from the prior frontend-stack-guide change MUST remain; API-contract sections MUST be added or corrected in the same file.

#### Scenario: Single canonical FE pointer

- **WHEN** a frontend developer or agent starts API client work
- **THEN** they MUST be able to use `docs/FE_guide.md` alone for stack rules plus endpoint/auth/DTO/SSE/GeoJSON/error guidance
- **AND** the guide MUST state that live routers + `src/*/schemas.py` (and OpenAPI `/docs`) win on conflict

#### Scenario: No FastAPI code changes required

- **WHEN** this change is applied
- **THEN** documentation updates MUST be sufficient
- **AND** FastAPI routes, cookies, and schemas MUST NOT be required to change for the guide to land

### Requirement: Endpoint auth and ownership matrix

`docs/FE_guide.md` MUST document every live MVP endpoint with Method, Path, Auth level, and ownership notes matching `docs/context.md` Live endpoints vocabulary (`None`, `Optional`, `Required`, plus guest-session / owner rules for trips).

#### Scenario: FE knows which calls need login

- **WHEN** implementing trip list, claim, delete, or day-edit clients
- **THEN** the guide MUST mark those routes as requiring auth (and ownership where applicable)
- **AND** MUST mark guest-capable routes (`POST /planner/generate`, `GET /trips/{id}`, public geojson/search) accordingly

#### Scenario: Destructive guest actions

- **WHEN** documenting `DELETE /trips/{id}`
- **THEN** the guide MUST state that anonymous delete is not allowed (auth required) even though guest GET may succeed via session ownership

### Requirement: Request and response DTO sketches

The guide MUST include TypeScript-oriented field sketches for public MVP DTOs used by the FE: auth me/user, destination out/readiness, place out, `PlanRequest`, trip out / trip place out, reorder/add-stop bodies, plus `ApiResponse`, `ErrorResponse`, and `PaginatedResponse` (including `page`/`size` query defaults).

#### Scenario: Typed client without reading Python first

- **WHEN** a FE author builds Zod schemas or `lib/api` types from the guide
- **THEN** required field names and nullability for the DTOs above MUST be present in the guide
- **AND** sketches MUST be labeled as mirrors of backend schemas (schemas win on drift)

#### Scenario: Envelope exceptions are explicit

- **WHEN** documenting response shapes
- **THEN** the guide MUST state that `GET /trips/{id}/geojson` returns a raw GeoJSON `FeatureCollection` (not `ApiResponse`)
- **AND** MUST state that `POST /planner/generate` streams SSE (not `ApiResponse`)
- **AND** MUST state that list endpoints for places and trips return `PaginatedResponse` directly (not wrapped in `ApiResponse`)
- **AND** MUST state that `DELETE /trips/{id}` returns HTTP 204 with no JSON body

### Requirement: Readiness fields match the live schema

The guide MUST document destination readiness using fields returned by `DestinationReadinessOut` (`destination_id`, `score`, `tier`, `place_count`, `enriched_pct`, `indexed_pct`, `message`) and MUST NOT instruct the FE to read a JSON field named `search_available`.

#### Scenario: Readiness UX correction

- **WHEN** the MVP screen flow describes readiness gating
- **THEN** UI guidance MUST use `tier` / `score` / counts / percentages / `message`
- **AND** MUST NOT claim `search_available` is present on the readiness response

### Requirement: SSE event catalog for planner generate

The guide MUST document progress vs terminal SSE events for `POST /api/v1/planner/generate`, with representative `data` keys for at least `preferences_done`, `phase_changed`, `tool_done`, `tool_batch_done`, `itinerary_done` (including post-save `trip_id` enrichment), `error`, and `clarification_needed`, and MUST note that cache replay may omit tool progress events.

#### Scenario: Progress UI can bind events

- **WHEN** implementing the generate progress screen
- **THEN** the guide MUST identify which events are terminal vs progress
- **AND** MUST advise navigating to the persisted trip via `trip_id` when present rather than treating the full SSE itinerary payload as the long-term UI model

#### Scenario: Pre-stream floor failure

- **WHEN** destination `place_count` is below the planner floor
- **THEN** the guide MUST document HTTP 409 `destination_not_ready` before any SSE stream starts

### Requirement: GeoJSON map contract

The guide MUST document the public trip GeoJSON contract: `FeatureCollection` with Point features (stop markers) and optional LineString features (day legs), including property names used by `TripService.build_geojson`.

#### Scenario: MapLibre consume geojson

- **WHEN** the FE loads `GET /api/v1/trips/{id}/geojson`
- **THEN** the guide MUST list Point properties including `name`, `day`, `order`, `suggested_start_time`, `place_id`, `trip_place_id`
- **AND** MUST note coordinates as GeoJSON `[lng, lat]`
- **AND** MUST list LineString properties including `day` and `trip_id`

### Requirement: Error codes and rate-limit UX notes

The guide MUST catalog FE-relevant error `code` values for toast/branching (`destination_not_ready`, `not_found`, `unauthorized`, `forbidden`, `rate_limit_exceeded`, `validation_error`, and other global handler codes that appear on MVP paths) plus SSE terminal error codes such as `generation_timeout` and `graph_recursion_limit`, and MUST summarize which MVP routes are rate-limited in ways that affect UX.

#### Scenario: Client maps codes to UX

- **WHEN** the shared API client receives `{ success: false, code, message }`
- **THEN** the guide MUST enable branching at least for not-ready, auth failures, validation, and rate limits without inventing undocumented codes

### Requirement: Source-of-truth and maintenance rule

The guide MUST state a source-of-truth order: (1) live routers + domain schemas, (2) OpenAPI at `/docs`, (3) `docs/context.md` Live endpoints, (4) `docs/FE_guide.md` as the FE-oriented mirror — and MUST require updating the FE guide contract sections when public routes or DTOs change.

#### Scenario: After an API contract change

- **WHEN** a backend change adds, removes, or reshapes a public FE-facing endpoint or DTO
- **THEN** maintainers MUST update the corresponding `docs/FE_guide.md` API-contract sections in the same change or immediately after
- **AND** MUST NOT leave the FE guide listing removed routes as live
