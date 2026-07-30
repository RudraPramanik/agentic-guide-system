## Context

P0–P3 are done: DB/auth, geo seed, enrichment, Qdrant index, readiness with live `search_available`. All files under `src/travel_engine/` and most `src/planner/*` remain **stubs** (~1-line placeholders) — do not assume APIs exist.

`docs/blueprint_final.md` **v6.1** is Planner SoT (pre-flight locks merged). `docs/steps/step4.md` is empty. P2/P3 succeeded because hardened step prompts locked contracts before Cursor apply. This design change authors that P4 prompt (and OpenSpec alignment), not the production code itself.

Constraints (AGENT.md): travel_engine has **no** LLM, network, or DB; routing via injected `RoutingProvider`; geo only through `src/geo/` (outside travel_engine); all env via `get_settings()`.

Sibling note: `openspec/changes/p4-travel-engine` already planned implementation but still carries some pre-v6.1 doc language in tasks. This design change’s apply deliverable (`step4.md`) becomes the implementation contract; supersede/archive the older change’s “author step4” intent after the prompt lands.

## Goals / Non-Goals

**Goals:**

- Author `docs/steps/step4.md` in the **step2/step3 shape**: Fix/decision log, prerequisites, architecture, locked decisions, sub-steps **4.0–4.10**, FAILURE BOUNDARY per code step, ✅ validation, pytest plan, smoke/real proof, ship checklist.
- Encode blueprint_final v6.1 locks: vocabulary split, sum scoring, permutation TSP, `dropped_stops`, naive wall-clock, DI routing, CORS, forward-only P5/P6 notes.
- Define clear abstractions: Protocol DI for routing; rules-as-data; strategy-style selector; template-method optimizer; chain-of-checks validator; adapter outside the pure core.
- Make every sub-step implementable without inventing either/or contracts.

**Non-Goals:**

- Implementing production travel_engine/CORS/planner code in *this* change’s apply (unless explicitly expanded later) — primary apply = write the prompt.
- LangGraph, full tool registry, SSE, trip CRUD, evaluation recording, Redis.
- Turning `blueprint_final.md` into a Cursor prompt or duplicating the whole blueprint into OpenSpec main specs.
- One OpenSpec propose→apply→archive ceremony per micro-step during implementation (see process decision below).

## Decisions

### D0 — Process: blueprint vs step prompt vs OpenSpec cadence

**Choice:** Keep three layers distinct:

| Layer | Role |
|-------|------|
| `docs/blueprint_final.md` | Product/architecture SoT |
| `docs/steps/step4.md` | Agent build contract (sub-steps, validation, tests) |
| OpenSpec change | Propose → apply → archive for *batches* of work |

**Apply cadence for P4 implementation (after this design change archives):** Prefer **one design change now**, then **batched implementation changes** (e.g. 4.0+4.1–4.2, 4.3–4.4, 4.5–4.6, 4.7–4.8, 4.9–4.10) — same as how P2/P3 were often clustered. Do **not** run full propose→archive for every 1–2 hour micro-step; that is process delay without quality gain when `step4.md` already locks the contract.

**Why this is not unnecessary:** P2/P3 v2 Fix Logs paid for the hardened prompt. P4 is simpler (pure Python) but still has vocabulary/DI/fallback footguns that must be locked once in `step4.md`. Skipping the prompt and coding from the blueprint alone tends to re-open either/or decisions mid-apply.

### D1 — Vocabulary split (blueprint_final v6.1)

**Choice:** Structural constants keyed by `Place.category` (P2). Interest weights keyed by `Place.enriched_tags` membership (P3 `PLACE_TAG_VOCAB`). Complete `VISIT_DURATION_BY_CATEGORY` for all P2 categories; `VISIT_DURATION_DEFAULT_MIN`; no `sunrise_point`; no interest-only duration keys.

**Alt:** Unified taxonomy — rejected (would re-seed P2 / re-enrich P3).

### D2 — Scoring = sum of matching interest weights

```
score = sum(CATEGORY_WEIGHTS[tag] for tag in place.enriched_tags
            if tag in CATEGORY_WEIGHTS and tag in user_interests)
```

Duration always `.get(category, VISIT_DURATION_DEFAULT_MIN)`.

### D3 — Route ordering = brute-force permutations

N ≤ `MAX_PLACES_PER_DAY` (6) → ≤720 orderings; fixed start at base lat/lng; call `routing.travel_matrix` once per candidate evaluation strategy locked in the prompt (prefer: build full pairwise matrix once, score permutations in-memory). **No TSP package.**

**Alt:** nearest-neighbor — rejected (harder deterministic tests).

### D4 — Drop-retry records `dropped_stops`

Max 3 drops of lowest-scored stop when travel > `MAX_DAILY_TRAVEL_MIN`. Emit `dropped_stops` for P5 REPLAN coordination (prefer expand search over further thinning).

### D5 — `explain_selection` → trace-shaped strings

Compact strings for tool_trace / rank_places — not a TripEvaluation schema migration.

### D6 — Protocols in travel_engine; OSRM adapter in planner

`RoutingProvider` + `RouteLeg` in `travel_engine/protocols.py`. `OsrmRoutingProvider` in `planner/routing_provider.py` wraps `geo/osrm.py` (existing tenacity 2× → haversine × 1.4 fallback) and maps `fallback_used` → `RouteLeg.used_fallback`.

### D7 — CORS now; SameSite Option A documented only

`CORSMiddleware` + `CORS_ALLOWED_ORIGINS` (never `*` with credentials). Cookie SameSite stays Lax for same-domain MVP — document in context.md; no auth code change in P4.

### D8 — Day times are wall-clock naive strings

`DAY_START_TIME` / lunch / suggested times are destination-local strings; travel_engine never attaches tz or converts to UTC.

### D9 — Budget filter soft until cost field exists

Place selector treats budget as soft preference on the preferences object; no invented hard cost exclude in P4.

### D10 — Geo coherence threshold is a named constant

`GEO_COHERENCE_MAX_STDDEV_KM` (or equivalent) lives in `travel_rules.py` — single tunable; exact default chosen in the prompt from a sensible mountain-town scale (document the number; no magic inline literals scattered in validator).

### D11 — Prompt build order (locked)

```
4.0 CORS
  → 4.1 protocols
    → 4.2 travel_rules
      → 4.3 place_selector
        → 4.4 day_allocator
          → 4.5 route_optimizer
            → 4.6 schedule_builder
              → 4.7 trip_validator
                → 4.8 OsrmRoutingProvider + execute_tool skeleton
                  → 4.9 pytest suite
                    → 4.10 smoke / real verification + context.md
```

`TravelTimeMatrix` as a distinct type is optional: default to `list[RouteLeg]` + a small helper for pair lookup if the optimizer needs it; only add a named type if the prompt’s API clarity requires it.

### D12 — Design patterns called out in the prompt (teaching + structure)

| Module | Pattern | Meaning in P4 |
|--------|---------|----------------|
| `travel_rules` | Configuration as data | Constants, not buried conditionals |
| `place_selector` | Strategy-friendly pure API | Scoring/filter testable in isolation |
| `route_optimizer` | Template method + DI | Algorithm fixed; routing injected |
| `trip_validator` | Chain of responsibility | One function per rule |
| `OsrmRoutingProvider` | Adapter | geo gateway → engine protocol |

### D13 — Verification bar (match step2 quality)

Every code step: import/unit proof. Phase closeout: expanded pytest (4.9) + `scripts/test_p4_smoke.py` (4.10) that runs select→allocate→optimize→schedule→validate on fixtures with `FakeRoutingProvider` (network optional section for live OSRM). Import guards: no `src.geo` under `travel_engine/`. Failures: non-zero exit + section headers.

## Risks / Trade-offs

- [Risk] Doc drift if someone edits blueprint without updating step4 → Mitigation: step4 cites blueprint_final section anchors; context.md points agents at step4 for build, blueprint for SoT.
- [Risk] Permutation search issues N! matrix calls → Mitigation: prompt locks “matrix once, score perms in memory.”
- [Risk] Empty `enriched_tags` → all scores 0 → Mitigation: document; still allocate; P5 search should prefer enriched places.
- [Risk] Drop-retry removes only anchor → VALIDATE fails → Mitigation: `dropped_stops` + validator messages; P5 guidance.
- [Risk] Over-process OpenSpec per micro-step → Mitigation: D0 batched applies.
- [Trade-off] Existing `p4-travel-engine` change overlaps → Treat this prompt as winning doc contract; archive/abandon stale implementation tasks that contradict v6.1.

## Migration Plan

1. Apply this change: write hardened `docs/steps/step4.md` (+ keep OpenSpec artifacts coherent).
2. Archive `design-step4-p4-travel-engine`.
3. Implement from the prompt in batched OpenSpec applies (or a single implementation change that checks off step4 sub-steps).
4. After 4.9/4.10 pass: update `docs/context.md`; adjust stubs list; mark P4 progress ✅.
5. Rollback of code later: revert module files; empty/explicit CORS origins deny cross-origin safely.

## Open Questions

None blocking for authoring the prompt. Defaults above (D9–D11) are locked for step4.md unless the user overrides before apply.
