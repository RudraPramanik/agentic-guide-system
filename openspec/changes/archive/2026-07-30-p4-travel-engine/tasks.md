## 1. Docs & pre-flight

- [ ] 1.1 Author `docs/steps/step4.md` as the P4 Cursor build prompt (4.0 CORS + 4.1–4.8), incorporating LOCKED items from `docs/blueprint.md` §§A.1, B, C (not the buggy v6 `travel_rules` draft in `blueprint_final.md`)
- [ ] 1.2 Record MVP cookie SameSite decision (Option A: same registrable domain / `Lax`) in `docs/context.md` as a locked deployment note (docs-only; no auth cookie code change)

## 2. CORS (addendum A.1)

- [ ] 2.1 Add `CORS_ALLOWED_ORIGINS: list[str]` to settings (env-configurable; include localhost frontend example in `.env.example` if present)
- [ ] 2.2 Register `CORSMiddleware` in `create_app()` with `allow_credentials=True` and explicit origins — never `["*"]` with credentials
- [ ] 2.3 Add a focused test or smoke assertion that CORS headers honor configured origins

## 3. Protocols & rules (4.1–4.2)

- [ ] 3.1 Implement `src/travel_engine/protocols.py` — `RouteLeg`, `RoutingProvider` (async `travel_matrix`)
- [ ] 3.2 Implement corrected `src/travel_engine/travel_rules.py` per design D1 (structural durations for all P2 categories + default; interest `CATEGORY_WEIGHTS`; no `sunrise_point`; no interest-only duration keys)
- [ ] 3.3 Proof: import `MAX_PLACES_PER_DAY` → 6; assert duration keys ⊇ `{museum,viewpoint,monastery,attraction,park,trailhead}`

## 4. Place selector & day allocator (4.3–4.4)

- [ ] 4.1 Implement `place_selector.select_places` with sum-of-matching-weights scoring, conflict filter, and `explain_selection` → str
- [ ] 4.2 Unit tests: multi-interest outranks single; conflict pairs removed; empty enriched_tags → score 0 still handled
- [ ] 4.3 Implement `day_allocator.allocate_days` with `MAX_PLACES_PER_DAY`, visit-time budget, geographic pre-clustering
- [ ] 4.4 Unit test: 18 places / 3 days → 3 lists each ≤6 and within visit-time budget

## 5. Route optimizer & schedule (4.5–4.6)

- [ ] 5.1 Implement `route_optimizer.optimize_route` with brute-force permutation ordering, drop-retry ≤3, and `dropped_stops` on result
- [ ] 5.2 Unit tests with `FakeRoutingProvider` (no network): optimal order; over-budget drops + reasons; no TSP package added
- [ ] 5.3 Implement `schedule_builder.build_day_schedule` — naive wall-clock times, lunch break, morning-only enforcement
- [ ] 5.4 Unit test: 6-stop day → times set; first ≥ `DAY_START_TIME`; viewpoint in slot 1–2

## 6. Trip validator (4.7)

- [ ] 6.1 Implement `trip_validator.validate_trip` → `ValidationResult` with named rule checks (travel cap, repeats, morning slots, anchor, geo coherence)
- [ ] 6.2 Unit tests: good itinerary `errors=[]`; injected violations produce specific error messages

## 7. Planner routing stub (4.8)

- [ ] 7.1 Implement `OsrmRoutingProvider` wrapping `geo/osrm.py`; map haversine fallback → `RouteLeg.used_fallback=True`
- [ ] 7.2 Add minimal `ToolResult` + `execute_tool` skeleton (unknown tool → `ok=False`, never raise); leave full registry to P5
- [ ] 7.3 Tests: fake provider path; unknown tool envelope; grep/assert no `src.geo` imports under `src/travel_engine/`

## 8. Verification & context

- [ ] 8.1 Run `python -m pytest tests/ -v` — all prior + new P4 tests green
- [ ] 8.2 Update `docs/context.md`: Last updated, Next step → P5.1, Progress rows for 4.0–4.8 ✅, Implemented modules for travel_engine + routing provider, stubs list adjusted
- [ ] 8.3 Optionally note in context or a short comment that `blueprint_final.md` travel_rules draft is superseded by `docs/blueprint.md` §B until a doc sync PR
