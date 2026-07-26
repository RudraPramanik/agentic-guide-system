## Why

P2.1–P2.8 are implemented, but P2 cannot be closed safely until their resilience, PostGIS, HTTP, and seed-pipeline contracts have deterministic regression coverage plus one end-to-end smoke proof. The current Step 2.9/2.10 prompts are close, but they treat same-session idempotency as race coverage, omit OSRM from smoke, leave radius assertions ambiguous, and incorrectly treat `place_count >= 50` as enough for unenriched `tier=limited` / `score >= 0.35`.

## What Changes

- Harden the canonical P2.9 and P2.10 prompts before implementation so each acceptance check is executable and maps to the actual APIs.
- Split live floors: Overpass/seed volume stays `>= 50`; unenriched readiness limited/`score >= 0.35` requires a formula-true floor (`place_count >= 88`, preferably `>= 100` for score exactly `0.4`).
- Amend readiness acceptance language in the step doc and related main specs so `place_count >= 50` is no longer claimed to imply limited-band scoring.
- Add mocked geo gateway tests for success parsing, cache behavior, query/coordinate construction, retries/fallback boundaries, and invalid OSRM input without calling public services in CI.
- Add pure readiness, destination/place repository, service/router, path-specific rate-limit, and PostGIS geography-radius coverage.
- Prove destination upsert concurrency with separate sessions/tasks, not two sequential calls in one session.
- Add deterministic seed-pipeline tests for partial POI failure and empty Overpass results; introduce only the smallest session-injected seam needed to avoid the development database in tests.
- Add `scripts/test_p2_smoke.py` as a sequential, fail-fast P2 proof covering live geo gateways, seed persistence/idempotency, full `/api/v1/...` HTTP paths, readiness, rate-limit headers, OSRM, and radius sanity with `limit >= place_count`.
- Update `docs/context.md` only after the complete P2 test suite and smoke proof pass.
- No new package installs and no production API or formula changes.

## Capabilities

### New Capabilities

- `p2-verification`: Deterministic P2 pytest coverage and the manual/live P2 smoke-test contract.

### Modified Capabilities

- `p2-step-doc`: Correct and tighten Steps 2.9/2.10 and the P2 completion checklist for concurrency, OSRM, exact radius assertions, formula-true readiness floors, Windows-safe commands, and non-duplicative context maintenance.
- `destination-readiness`: Fix unenriched service/acceptance scenarios so limited-band claims use a place-count floor that the locked formula can actually produce.
- `destinations-http`: Fix the seeded Darjeeling readiness HTTP scenario the same way (volume floor vs readiness floor).

## Impact

- Affected documentation: `docs/steps/step2.md`, `docs/context.md`.
- New tests: `tests/geo/`, `tests/destinations/`, `tests/places/`, and `tests/scripts/`.
- New script: `scripts/test_p2_smoke.py`.
- Possible narrow refactor: `scripts/seed_destination.py` to expose a session-injected pipeline helper while preserving CLI behavior.
- Existing runtime modules are exercised but their public HTTP, repository, and geo contracts remain unchanged.
- Relevant guardrails: external HTTP is mocked in pytest; geo access remains under `src/geo/`; routers continue to call services only; settings come from `get_settings()`; no new dependencies.

## Non-goals

- Implementing P3 enrichment, Qdrant search, or changing readiness to report `ready` before enrichment.
- Replacing process-local geocoder/rate-limit state with Redis (deferred to P6).
- Making CI depend on live Nominatim, Overpass, or OSRM.
- Broad refactoring of already implemented P2 production modules.
