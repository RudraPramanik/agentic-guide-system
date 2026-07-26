## Purpose

Canonical P2 Cursor prompt document standards — locked geo/readiness decisions, concurrency-safe upsert rules, failure-boundary proofs, and a single build order for Agent mode.

## Requirements

### Requirement: Canonical P2 step document exists

The project SHALL maintain a single canonical `docs/steps/step2.md` for Phase P2 Cursor prompts. Duplicate draft files (e.g. `suggestedp2.md`) SHALL NOT remain after finalize.

#### Scenario: Agent starts P2

- **WHEN** an agent or developer begins P2 implementation
- **THEN** they use only `docs/steps/step2.md` and that file’s header identifies it as the hardened v2 prompts

### Requirement: P2 prompts forbid async lru_cache on geocode

`docs/steps/step2.md` SHALL instruct implementers to use a manual resolved-value cache for `geocode()`, and SHALL NOT instruct `@functools.lru_cache` on `async def geocode`.

#### Scenario: Cache-hit validation

- **WHEN** step 2.1 validation runs a second `await geocode` for the same query
- **THEN** the documented expected outcome is a successful return (not RuntimeError) with a measurable cache hit

### Requirement: P2 prompts require atomic external-ID upserts

`docs/steps/step2.md` SHALL require repository writes keyed by unique external IDs (`osm_id`, `osm_place_id`) to use a single `INSERT ... ON CONFLICT ... DO UPDATE` (with RETURNING where applicable), not check-then-insert.

#### Scenario: Destination geocode upsert

- **WHEN** two requests would insert the same `osm_place_id`
- **THEN** the step doc requires an atomic upsert so the failure mode is not an unhandled IntegrityError 500

### Requirement: P2 prompts lock radius search to geography

`docs/steps/step2.md` SHALL lock `find_within_radius` to cast both sides to PostGIS `geography` and use meter distances. It SHALL NOT leave geometry-vs-geography as an implementer choice.

#### Scenario: Radius unit decision

- **WHEN** an agent implements step 2.3
- **THEN** the prompt specifies geography cast and explains that plain geometry SRID 4326 measures degrees

### Requirement: P2 prompts include destinations search rate limit step

`docs/steps/step2.md` SHALL include a dedicated step that extends P1 `RateLimitMiddleware` / `_resolve_limits` with a path-specific limit for `GET /api/v1/destinations/search` (20 requests per minute per IP).

#### Scenario: Search path limit documented

- **WHEN** an agent completes destinations router wiring
- **THEN** a following step documents config keys and validation for the search-specific rate limit

### Requirement: P2 prompts mandate destination existence on places list

`docs/steps/step2.md` SHALL require `PlaceService.list_by_destination` to raise `DestinationNotFoundError` (404) when the destination does not exist — not return an empty paginated list.

#### Scenario: Garbage destination_id

- **WHEN** `GET /api/v1/places?destination_id=` uses an unknown UUID
- **THEN** the step doc’s expected behavior is 404, not `total=0`

### Requirement: P2 prompts state a single canonical build order

`docs/steps/step2.md` SHALL state exactly one build order that places destination repository/service (2.6a/b) before the seed script (2.4), and SHALL NOT rely on a separate “amendment” note that contradicts step numbering.

#### Scenario: Seed depends on destination upsert

- **WHEN** an agent reaches the seed script step
- **THEN** `DestinationRepository.upsert_from_geocoded` is already specified as implemented in a prior step

### Requirement: P2 prompts include failure proofs for geo gateways

Each geo gateway and seed step in `docs/steps/step2.md` SHALL include a `FAILURE BOUNDARY` section and at least one verifiable `Failure path` validation aligned with blueprint resilience contracts (Nominatim → None, Overpass → [], OSRM → haversine fallback).

#### Scenario: Geocoder network failure

- **WHEN** step 2.1 failure-path validation is run with a mocked connect error
- **THEN** the documented expected outcome is `geocode` returning `None`

### Requirement: P2 prompts define an executable verification closeout

`docs/steps/step2.md` SHALL define Steps 2.9 and 2.10 in terms that can be implemented and validated against the current P2 APIs. Step 2.9 MUST distinguish sequential idempotency from concurrent upsert safety, require separate committed sessions for the race proof, keep public network calls out of pytest, identify a session-injected seed seam for database tests, and pin readiness unit fixtures including the regression that `place_count=50` is sparse. Step 2.10 MUST include OSRM, define exact idempotency and geography-radius assertions with `limit >= place_count`, use full `/api/v1/...` paths, split Overpass/seed volume (`>= 50`) from readiness limited-band floors (`place_count >= 100` preferred), and use fail-fast smoke output. Context maintenance instructions MUST update only facts not already recorded after P2.7b/P2.8.

#### Scenario: Agent begins Step 2.9

- **WHEN** an agent reads the canonical Step 2.9 prompt
- **THEN** the requested test set includes deterministic geo fallbacks, readiness and HTTP contracts, PostGIS radius units, seed failure boundaries, same-session counter preservation, a true separate-session concurrent destination upsert, and an explicit sparse assertion for unenriched `place_count=50`

#### Scenario: Agent begins Step 2.10

- **WHEN** an agent reads the canonical Step 2.10 prompt
- **THEN** the smoke sections include Nominatim cache behavior, Overpass volume `>= 50`, seed persistence/idempotency, full public P2 HTTP routes, formula-true readiness floors, path-specific rate-limit headers, OSRM-or-fallback routing, and an explicit geography-radius invariant with sufficient `limit`

#### Scenario: Agent completes P2 verification

- **WHEN** focused P2 tests, the full suite, and the smoke script pass
- **THEN** the prompt directs the agent to mark P2.9/P2.10 complete, retain known limitations, and set P3.1 next without re-adding existing module or endpoint rows

### Requirement: P2 completion commands are usable on Windows

The P2 completion checklist SHALL identify commands that require a separate long-running server terminal and SHALL use PowerShell-compatible executable names and syntax where platform aliases differ. The checklist MUST NOT present a blocking Uvicorn command followed by HTTP commands as if the entire block runs sequentially in one terminal.

#### Scenario: Developer follows the PowerShell checklist

- **WHEN** a Windows developer reaches the server and HTTP verification sections
- **THEN** the document tells them to keep Uvicorn in a separate terminal and uses `curl.exe` or an equivalent PowerShell-safe command for curl flags
