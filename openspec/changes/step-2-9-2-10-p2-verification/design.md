## Context

P2.1–P2.8 have real implementations, while `tests/` still contains only P1 coverage and `scripts/test_p2_smoke.py` does not exist. Steps 2.9 and 2.10 in `docs/steps/step2.md` define the intended closeout, but several statements are not strong enough to prove the contracts they name:

- two sequential upserts in one session prove idempotency, not concurrent conflict safety;
- the empty-Overpass seed test has no clean way to use `db_session` with the current script-owned session factory;
- the smoke outline does not exercise OSRM;
- “roughly consistent” radius results clash with `find_within_radius(..., limit=100)`;
- unenriched readiness acceptance still says `place_count >= 50` while the locked formula yields score `0.2` / `sparse` at 50;
- the context update repeats modules/endpoints already recorded after P2.7b/P2.8.

The change spans tests, a smoke script, the seed-script test seam, and canonical step documentation. It must preserve all production endpoint and repository contracts.

## Goals / Non-Goals

**Goals:**

- Make Step 2.9 deterministic in CI: no calls to Nominatim, Overpass, or OSRM.
- Cover each P2 resilience fallback, critical regression, HTTP boundary, and PostGIS unit contract.
- Prove atomic destination upsert behavior under actual concurrent transactions.
- Make seed partial-failure and empty-result behavior testable against `wandr_test`.
- Provide one sequential, fail-fast P2 smoke command with clear Windows-safe output.
- Reconcile the canonical step prompt before implementation and update context only after validation.

**Non-Goals:**

- Change P2 runtime APIs, database schema, the locked readiness formula, or rate limits.
- Add packages or introduce a general-purpose testing framework.
- Make live external services part of pytest/CI.
- Implement P3 enrichment/search or the P6 Redis migration.

## Decisions

### 1. Correct the canonical prompt before writing tests

`docs/steps/step2.md` remains the implementation source of truth. Step 2.9 will distinguish sequential idempotency from a true race test, name the required separate-session pattern, and make the seed test seam explicit. Step 2.10 will include OSRM, define exact radius/idempotency checks, split volume vs readiness floors, and limit the final context update to P2.9/P2.10 completion facts. Matching main-spec scenarios in `destination-readiness` and `destinations-http` will be amended in the same change.

Alternative considered: leave the prompt untouched and explain deviations only in tests. Rejected because future agents are required to implement from the canonical step document.

### 2. Separate deterministic pytest from live smoke validation

Pytest will patch the boundary helpers imported by the module under test (`_fetch_nominatim`, `_post_overpass`, `_call_osrm`, and service-level imports where appropriate). Tests will assert mapped values, query/coordinate construction, cache behavior, named fallbacks, HTTP envelopes, and database effects without public network access.

The smoke script will intentionally use real configured geo providers and the development database. Every section will print `[OK]` or `[FAIL]`, stop on the first failed invariant, and return a non-zero process code on failure. Live Overpass/seed volume keeps `>= 50`. Unenriched readiness limited-band checks use a separate formula-true floor (`place_count >= 100` preferred; `>= 88` minimum for `score >= 0.35`). Failures report the observed count.

Alternative considered: run live geo tests under a pytest marker. Rejected because accidental CI selection would make the suite slow and flaky.

### 3. Use separate committed transactions for the destination race proof

The race test will create two `AsyncSession` instances from the test engine and run workers concurrently. Each worker executes `upsert_from_geocoded`, commits inside the worker, and returns the destination id. The test then asserts both ids are equal and one row exists for the `osm_place_id`.

Committing inside each worker is necessary: if both execute calls are awaited before either transaction commits, PostgreSQL can leave the second `ON CONFLICT` statement waiting on the first transaction.

Alternative considered: call the upsert twice through `db_session`. Retained as a separate idempotency/counter-preservation test, but it is not race coverage.

### 4. Add one narrow session-injected seed pipeline seam

The script will expose an async helper that accepts an `AsyncSession` and performs the geocode/upsert/fetch/seed/count-update pipeline without opening a session or committing. The existing CLI-facing wrapper will continue to own `AsyncSessionLocal`, commit on success, and return process exit codes.

This lets tests pass `db_session`, patch geo gateway results, and inspect rows without touching the development database. `seed_places` remains the direct unit for SAVEPOINT-based partial failure.

Alternative considered: monkeypatch `AsyncSessionLocal` with a fake async context manager. Rejected as coupling tests to script construction rather than behavior.

### 5. Split volume floors from readiness floors

Locked unenriched formula with `search_available=False`:

`score = round(0.4 * min(place_count / 100, 1.0), 3)`

So:

| place_count | score | tier |
|---|---|---|
| 50 | 0.2 | sparse |
| 75 | 0.3 | limited |
| 88 | 0.352 | limited |
| ≥100 | 0.4 | limited |

Acceptance therefore uses two independent floors:

- Overpass/seed volume: `>= 50` (enough POIs seeded)
- Readiness limited + `score >= 0.35`: `place_count >= 100` preferred; never claim this from `>= 50`

Unit tests continue to use the known good fixture `(144, 0, 0, False)`.

Alternative considered: lower the limited threshold. Rejected — the formula is locked; only acceptance language is wrong.

### 6. Make smoke assertions explicit and bounded

The smoke script will:

1. clear the geocoder cache, geocode Darjeeling twice, and verify the second call increments cache hits;
2. fetch at least 50 POIs;
3. run the seed pipeline and verify persisted counters;
4. reapply the already-fetched POIs to prove idempotent OSM upserts without a second Overpass call;
5. call full `/api/v1/destinations/search`, `/api/v1/places`, and `/api/v1/destinations/{id}/readiness` through ASGI transport;
6. require the search response header `x-ratelimit-limit: 20`;
7. require readiness `tier=limited` and `0.35 <= score <= 0.45` only when `place_count >= 100` (fail with observed count otherwise);
8. call OSRM and require a positive route result (real route or named fallback);
9. call `find_within_radius` with `limit >= place_count` and require all just-seeded places to be found.

The smoke script will not start an external Uvicorn process. HTTP proof uses the app in-process while still exercising middleware, routers, services, and the development database.

### 7. Keep repository and HTTP contracts unchanged

Tests may create ORM fixtures directly, but routers remain Router → Service → Repository. All external HTTP remains under `src/geo/`, and no test-only switch is added to production settings. Geocoder ConnectError tests MUST account for tenacity’s 3 attempts on `_fetch_nominatim` before the public `geocode` returns `None`.

## Risks / Trade-offs

- [Public Overpass data or service availability changes] → Keep live checks out of pytest; keep volume floor at `>= 50`; require a separate readiness floor (`>= 100`) and fail with observed counts when either floor is missed.
- [A seed of 50–87 places looks “successful” but fails limited-band readiness] → Document and assert the floors separately so a sparse-band seed is not mislabeled as limited.
- [Concurrent test hangs because transaction ownership is wrong] → Commit within each independently created session worker and apply a bounded async timeout to the gather.
- [Process-global geocoder cache leaks between tests] → Use the existing `_clear_cache_for_tests()` in an autouse fixture for the geocoder module.
- [Process-global rate limiter leaks request counts] → Patch the limiter backend per path-specific test and restore it after each test.
- [Smoke writes development data] → State this in the script docstring; rely on atomic upserts so reruns are safe.
- [Seed helper refactor changes CLI semantics] → Keep argument parsing, exit codes, session ownership, commit behavior, and output in the wrapper; cover geocode failure and empty Overpass explicitly.

## Migration Plan

1. Update the Step 2.9/2.10 prompt and completion checklist.
2. Add deterministic tests and the seed session seam.
3. Run focused P2 tests, then the complete pytest suite.
4. Add and run the live P2 smoke script with Docker services available.
5. Update `docs/context.md` to mark P2.9/P2.10 complete and set P3.1 next.

Rollback is file-level: remove the new tests/smoke script, revert the seed helper extraction, and restore the prior prompt. No database migration or API rollback is required.

## Open Questions

None. The locked formula, current gateway symbols, and seed helpers already define the contracts; only acceptance language and verification coverage need to catch up.
