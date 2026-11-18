## Context

See `proposal.md` for motivation. Checkout facts that shape the approach:

- `place_selector.select_places` / `score_place` are pure v6.1 sum-of-matching-weights + `AVOID_SAME_DAY_PAIRS` greedy filter. `PlaceCandidate.id` is the canonical id field.
- `rank_places` always ranks; `build_route` may auto-rank from `candidate_pois` when `ranked_pois` is empty — both must share one gate or V2 can be bypassed.
- `TRAVEL_ENGINE_V2_ENABLED` is blueprint-only today (`docs/v8.2/repository_audit.md`). Architecture helpers already know the default `false` when the field appears.
- `tests/travel_engine/test_properties.py` skips idempotent dedup (“slice 4.1 owns candidate normalizer”) and asserts engine sources do not contain `TRAVEL_ENGINE_V2_ENABLED`.
- Places expose `osm_id` + `enriched_tags`; there is no alias/parent ORM. Evidence is not a first-class stored type yet.
- Slice 2 harness / replay gate is closed; flag-off generate must stay non-regressing on `--replay`.

## Goals / Non-Goals

**Goals:**

- Ship a pure normalizer + V2 scoring terms with a real kill-switch that tools honor.
- Keep `travel_engine/` free of settings/I/O; inject `v2_enabled: bool` (or equivalent) at the tool boundary.
- Prove monastery-variant collapse, adjacent-attraction retention, user-selected retention, flag-off byte identity, and idempotent dedup in pytest.
- Sync `docs/context.md` + audit rows when verify is green.

**Non-Goals:**

- Allocator / optimizer / schedule / validator V2 (4.3–4.6).
- Renaming `id` → `place_id`, new HTTP/SSE fields, FE work.
- Inventing OSM alias graphs or a new evidence store beyond optional candidate fields + rules constants.

## Decisions

### 1. Inject the flag; do not read settings inside travel_engine

**Choice:** `Settings.TRAVEL_ENGINE_V2_ENABLED` (default `false`). `rank_places` and `build_route` auto-rank call `get_settings()`. Pure APIs take `*, v2_enabled: bool = False` (and normalizer is only invoked when true).

**Why:** Preserves G2 purity and keeps the property suite honest: engine files never contain the setting name. Alternatives rejected: (a) `get_settings()` inside `place_selector` — violates pure-engine rule; (b) dark library with unread flag — not feature-proof for 4.1–4.2 verify lines that require flag-off identity under generate-adjacent paths.

### 2. One shared helper for normalize-then-select

**Choice:** Add a small pure helper in `travel_engine` (e.g. `rank_candidates(candidates, prefs, *, v2_enabled)`) **or** a planner `_helpers` function that calls `normalize_candidates` then `select_places(..., v2_enabled=...)`. Prefer the travel_engine helper so both tools stay thin and tests can hit one path without FastAPI.

**Why:** `build_route` already duplicates `select_places`. Feature-proof requires both sites. Alternative rejected: only wire `rank_places` — auto-rank would silently keep v6.1 under a true flag.

### 3. Adapt `PlaceCandidate`; do not fork a §6.4 twin type

**Choice:** Keep `id`. Add optional fields with defaults: `user_selected: bool = False`, `aliases: list[str] = []`, `parent_place_id: UUID | None = None`, `source: str | None = None`, `source_id: str | None = None`, `evidence_count: int = 0` (or a small `list[str]` of opaque ref tokens). Map `osm_id` → `source_id` / `source="osm"` in `_helpers.place_to_candidate` when present.

**Why:** Conflict rule — existing code is authoritative for field names. Alternatives rejected: rename to `place_id` (breaks every tool/test); full `EvidenceRef` model with timestamps (no producer yet; overbuilds 4.2).

### 4. Dedup policy: confidence ladder, no aggressive geo merge

**Choice:** Ordered rules, first decisive wins, keep highest-confidence / user-selected survivor:

1. Exact `id`
2. Normalized name equality within `NORMALIZER_PROXIMITY_M` (meters, from `travel_rules`)
3. Alias hit (candidate `aliases` or a tiny static map in `travel_rules` for known monastery spelling variants used in fixtures)
4. Parent/child when `parent_place_id` points at another candidate and confidence ≥ threshold

Different normalized names + no alias/parent ⇒ **both keep**, even if close. Collapse reasons optional for explanations/tests.

**Why:** Matches blueprint “no aggressive merging” and the monastery vs adjacent-attraction acceptance cases. Alternative rejected: clustering all points within N meters into one place — fails the adjacent-attraction scenario.

### 5. V2 score = base sum + additive configured terms

**Choice:**

```
score = sum(matching CATEGORY_WEIGHTS)
      + W_DIVERSITY * diversity_term
      + W_GEO_FIT * geo_fit_term
      + W_EVIDENCE * evidence_term
      + W_DUP_PENALTY * dup_penalty_term   # typically ≤ 0
```

Terms are pure functions of the candidate set / optional fields / trip prefs (e.g. diversity = novelty of structural category among already-scored peers during selection walk, or a pre-pass category rarity; geo fit = inverse distance to trip base if base coords are passed into scoring context, else 0; evidence = clamp(evidence_count); dup penalty = 0 after normalizer, or residual soft penalty if a near-dup survived user-selected retention). All `W_*` live in `travel_rules`. Default weights chosen so **unit fixtures** prove directionality; any weight that changes golden preference outcomes needs a golden case or the task stops (row 4.2 stop).

**Why:** Blueprint keeps v6.1 base and adds configured terms. Alternative rejected: replace sum scoring — would break flag-off identity and existing selector tests.

### 6. Explanations stay in existing `explanations` list

**Choice:** Extend `score_breakdown` keys; `explain_selection` already prints all breakdown pairs. No new `ToolResult` key and no SSE change.

### 7. Property suite evolution

**Choice:** Implement `test_idempotent_dedup` against `normalize_candidates`. Replace `test_engine_does_not_read_v2_flag` with scan-for-setting-name + `get_settings` ban in `src/travel_engine/**`, plus a unit assertion that `v2_enabled=False` matches legacy totals on a fixture. Leave area-respect as the location-intelligence containment test (already unskipped by Slice 3).

### 8. Settings / docs wiring exception

**Choice:** Same as Slice 3: `src/config.py` + `.env.example` + tool files are outside the §9 path cell but required for a real kill-switch. Completion sync only `docs/context.md` and travel-engine/flag rows in `docs/v8.2/repository_audit.md`.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| V2 weights regress preference goldens without evidence | Ship conservative defaults; add golden only when proving a weight; halt per row 4.2 stop if a change needs an unevidenced weight |
| Auto-rank and `rank_places` drift | Shared helper + tests covering both call sites |
| Optional fields break old candidate dicts | Defaults + validation test on legacy keys only |
| Static alias map becomes a junk drawer | Keep map tiny and fixture-driven; prefer candidate-carried `aliases` when available |
| Normalizer changes lat/lng unexpectedly | Compare on snapped keys; survivors keep original coords |
| Flag-on path slower | Pure CPU only; no I/O; still inside existing generate budget |

## Migration Plan

1. Land code with `TRAVEL_ENGINE_V2_ENABLED=false` (default).
2. CI: `pytest tests/travel_engine -k normalizer` / full `tests/travel_engine`, planner tool tests for the gate, `python scripts/run_evals.py --replay` (flag off).
3. Enable flag in a non-prod env to compare duplicate rate / preference metrics; do not flip production default in this change.
4. Rollback: set flag false (instant). Code rollback = revert PR if needed.

## Open Questions

None that block specs or tasks. Weight numeric defaults are implementation-time choices constrained by fixtures and the golden-evidence stop.
