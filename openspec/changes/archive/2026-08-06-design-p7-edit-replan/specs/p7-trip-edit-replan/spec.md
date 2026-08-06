## ADDED Requirements

### Requirement: P7 Cursor build contract exists

The project SHALL provide `docs/steps/step7.md` as the canonical P7 Cursor build contract covering steps **7.0–7.5**, with a Decision/Fix Log, shared locks (auth, failure boundaries, abstractions, design patterns, guardrails), pasteable Agent prompts, ✅ validation commands, ship criteria, and recommended OpenSpec implementation batches. The contract MUST follow the layering model of `docs/steps/step5.md` / `step6.md`: blueprint = product SoT; step7.md = build contract; OpenSpec = batched apply.

#### Scenario: Step7 file is non-empty contract

- **WHEN** an agent opens `docs/steps/step7.md` after this change is applied
- **THEN** the file defines steps 7.0–7.5 and a Decision/Fix Log (not an empty placeholder)

### Requirement: Day-scoped edit HTTP API

The system SHALL expose these authenticated endpoints under `/api/v1/trips`:

| Method | Path | Body |
|--------|------|------|
| PATCH | `/{id}/days/{day}/stops/reorder` | `{ "place_ids": [uuid, ...] }` |
| DELETE | `/{id}/days/{day}/stops/{place_id}` | — |
| POST | `/{id}/days/{day}/stops` | `{ "place_id": uuid }` |
| POST | `/{id}/days/{day}/reoptimize` | — |

Each successful response MUST be `ApiResponse[TripOut]` with the updated trip (places eager-loaded). All four MUST use `require_auth` and ownership (`trip.user_id == caller`); guests MUST NOT edit via session alone. Ownership miss → 403; missing/soft-deleted trip → 404.

#### Scenario: Owner reorder returns TripOut

- **WHEN** the authenticated owner PATCHes reorder with a valid permutation of day stops
- **THEN** the response is 200 `ApiResponse[TripOut]` and stop `order_in_day`, times, and polylines reflect the new order

#### Scenario: Guest cannot edit

- **WHEN** an unauthenticated or guest-only caller invokes any P7 edit endpoint
- **THEN** the response is 401 (or auth challenge) and the trip is unchanged

#### Scenario: Non-owner is forbidden

- **WHEN** an authenticated user who does not own the trip calls a P7 edit endpoint
- **THEN** the response is 403 and the trip is unchanged

### Requirement: Edit path uses travel_engine not planner agent

`TripService` edit operations MUST call pure `travel_engine` functions and an injected `RoutingProvider` (`OsrmRoutingProvider` in production, Fake in tests). They MUST NOT call `PlannerService`, `execute_tool`, LangGraph, or planner tool implementation modules. No LLM calls on the edit path.

#### Scenario: Service has no PlannerService dependency

- **WHEN** `TripService` edit methods are inspected / imported
- **THEN** they do not import or invoke `PlannerService` or `execute_tool`

### Requirement: Per-op day surgery semantics

The system SHALL apply these semantics:

- **reorder:** `place_ids` MUST be a permutation of that day’s current place_ids; preserve client order; recompute travel times via matrix for consecutive legs, `build_day_schedule`, and polylines; MUST NOT call `optimize_route` (no TSP reorder).
- **remove:** delete the stop; if the day would have zero stops → 422; else `optimize_route` + schedule + polylines for remaining stops.
- **add:** insert place at end of day then `optimize_route` + schedule + polylines; reject wrong destination or duplicate `trip_id+place_id`.
- **reoptimize:** `optimize_route` + schedule + polylines for current day stops.

Hydration to `ScoredPlace` MUST use Place coords/category/tags via `to_shape` and **score=1.0** (no re-ranking).

#### Scenario: Reorder preserves user order

- **WHEN** owner reorders day stops to a specific permutation
- **THEN** persisted `order_in_day` matches that permutation (engine does not silently TSP-permute)

#### Scenario: Remove last stop rejected

- **WHEN** owner deletes the only remaining stop on a day
- **THEN** response is 422 and the stop remains

#### Scenario: Add overload rolls back

- **WHEN** adding a stop causes `validate_trip` errors
- **THEN** response is 422 with validation details and no TripPlace / TripEditEvent rows are committed for that attempt

### Requirement: Validation failure rolls back

After an edit mutation attempt, the system MUST run `validate_trip` on a rebuilt itinerary. If validation `errors` is non-empty, the transaction MUST roll back, the trip MUST be unchanged, and the HTTP response MUST be 422 `ErrorResponse` including validation details. OSRM / routing fallback MUST NOT produce HTTP 500; haversine / null polyline with 200 is required when routing falls back.

#### Scenario: OSRM fail during reoptimize

- **WHEN** OSRM is unavailable during reoptimize and the provider falls back
- **THEN** the response is 200 (not 500) and the day times are updated (polylines may be null)

### Requirement: TripEditEvent on every successful edit

Each successful P7 edit MUST insert a `TripEditEvent` with the correct `EditType` (`reorder` | `remove_stop` | `add_stop` | `reoptimize_day`), `day_number`, optional `place_id`, and `payload` containing before/after stop snapshots, in the same transaction as the TripPlace mutations.

#### Scenario: Successful reorder writes audit row

- **WHEN** reorder succeeds
- **THEN** a `TripEditEvent` with `edit_type=reorder` exists for that trip_id
