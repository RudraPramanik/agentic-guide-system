## 1. Reconcile the canonical P2 closeout

- [ ] 1.1 Update `docs/steps/step2.md` Step 2.9 to distinguish same-session idempotency/counter preservation from a bounded separate-session concurrent upsert test.
- [ ] 1.2 Update Step 2.9 with deterministic geo contract cases, the session-injected seed seam, exact path-specific rate-limit and geography-radius assertions, and an explicit sparse regression for unenriched `place_count=50`.
- [ ] 1.3 Update Step 2.8/2.10/ship-criteria readiness language to split Overpass/seed volume (`>= 50`) from limited-band readiness (`place_count >= 100` preferred; never claim limited from `>= 50` alone).
- [ ] 1.4 Update Step 2.10 with OSRM, full `/api/v1/...` paths, fetched-POI reuse for idempotency, `find_within_radius(..., limit >= place_count)`, fail-fast section behavior, and non-duplicative context instructions.
- [ ] 1.5 Make the P2 completion checklist PowerShell-safe by separating the Uvicorn terminal and using `curl.exe`-compatible commands.

## 2. Add deterministic geo and readiness coverage

- [ ] 2.1 Create `tests/geo/test_geocoder.py` with cache reset isolation, success mapping, normalized cache hit, cached `None`, and contained HTTP failure cases that allow for tenacity’s up to 3 fetch attempts.
- [ ] 2.2 Create `tests/geo/test_overpass.py` with node/way parsing, category mapping, invalid-element filtering, last-wins deduplication, meter-radius query, and empty fallback cases.
- [ ] 2.3 Create `tests/geo/test_osrm.py` with successful unit conversion, `lng,lat` request construction, empty/error fallback, and insufficient-waypoint cases.
- [ ] 2.4 Create `tests/destinations/test_readiness.py` for sparse `(0,...)` and `(50,0,0,False)`, limited `(144,0,0,False)`, and ready `(144,100,100,True)` outputs including percentages and messages.
- [ ] 2.5 Run `python -m pytest tests/geo tests/destinations/test_readiness.py -v` and fix all failures without enabling live network access.

## 3. Add seed and repository database coverage

- [ ] 3.1 Refactor `scripts/seed_destination.py` to expose a session-injected pipeline helper while preserving CLI argument parsing, output, session ownership, commits, and exit codes; keep existing `seed_places` as the partial-failure unit.
- [ ] 3.2 Create `tests/scripts/test_seed_destination.py` covering one failed POI out of three, empty Overpass persistence with `place_count=0` via the session-injected helper (not CLI `AsyncSessionLocal`), and fatal geocode failure.
- [ ] 3.3 Create `tests/destinations/test_destinations_repository.py` for sequential idempotency and preservation of all denormalized counters.
- [ ] 3.4 Add a bounded concurrent destination upsert test using two sessions from `test_engine`, commit inside each worker, and assert one final OSM row with one shared id.
- [ ] 3.5 Create `tests/places/test_places_repository.py` with a known approximately 3 km fixture that is included at 5 km and excluded at 1 km.
- [ ] 3.6 Run `python -m pytest tests/scripts tests/destinations/test_destinations_repository.py tests/places/test_places_repository.py -v`.

## 4. Add destinations and places HTTP coverage

- [ ] 4.1 Create `tests/destinations/test_destinations_router.py` for successful search against `/api/v1/destinations/search`, geocode miss 404, readiness response for a destination with `place_count >= 100`, and unknown readiness destination.
- [ ] 4.2 Add a destinations-search rate-limit test that denies only the full `/api/v1/destinations/search` path key, asserts 429 and limit 20, and proves health remains allowed under the default route limit.
- [ ] 4.3 Create `tests/places/test_places_router.py` for paginated list metadata, successful get mapping, unknown place 404, and unknown destination 404 rather than an empty page.
- [ ] 4.4 Run `python -m pytest tests/destinations tests/places -v`.

## 5. Implement the P2 smoke proof

- [ ] 5.1 Create `scripts/test_p2_smoke.py` with sequential `[OK]`/`[FAIL]` sections, a non-zero failure exit, and the exact success sentinel.
- [ ] 5.2 Add live geocoder/cache (after cache clear), Overpass `>= 50`, seed persistence, and same-fetched-list idempotency checks.
- [ ] 5.3 Add in-process ASGI checks for `/api/v1/destinations/search`, paginated `/api/v1/places`, readiness with formula-true limited floor (`place_count >= 100`), and `x-ratelimit-limit: 20`.
- [ ] 5.4 Add a positive OSRM-or-fallback route check and a geography-radius check whose query limit can return every just-seeded place.
- [ ] 5.5 With Docker services and network available, run `python scripts/test_p2_smoke.py` and confirm the final line is `ALL P2 SMOKE TESTS PASSED`.

## 6. Validate and record P2 completion

- [ ] 6.1 Run `python -m pytest tests/geo tests/destinations tests/places tests/scripts -v`.
- [ ] 6.2 Run `python -m pytest tests/ -v` and confirm the complete P1+P2 suite is green.
- [ ] 6.3 Run the PowerShell-compatible P2 completion/import-guard checklist from `docs/steps/step2.md`.
- [ ] 6.4 Update `docs/context.md`: mark P2.9/P2.10 done, record the P2 tests/smoke script, retain per-process limitations, and set P3.1 next without duplicating existing P2 module/endpoint rows.
