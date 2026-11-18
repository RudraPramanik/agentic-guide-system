## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §6.4, §7.1, §9 rows 4.1–4.2, §11.6, plus this change's `proposal.md`, `design.md`, and delta specs under `specs/`. There is no `docs/steps/step*.md` for these rows.
- [x] 1.2 Keep production edits to: `src/travel_engine/candidate_normalizer.py` (new), `src/travel_engine/place_selector.py`, `src/travel_engine/travel_rules.py`, `src/planner/tools/rank_places.py`, `src/planner/tools/build_route.py`, `src/planner/tools/_helpers.py`, `src/config.py`, `.env.example`, `tests/travel_engine/**`, planner tool tests as needed, `docs/context.md`, and travel-engine/flag rows in `docs/v8.2/repository_audit.md`. Do not edit allocator/optimizer/schedule/validator, `VALIDATOR_V2_ENFORCE`, FE docs, Alembic, or `requirements.txt`. Do not rename `PlaceCandidate.id`.

## 2. Settings

- [x] 2.1 Add `TRAVEL_ENGINE_V2_ENABLED: bool = False` to `Settings` in `src/config.py`. Comment that tools inject the value into the pure engine; the engine package must not read it. Read only through `get_settings()` at the tool boundary.
- [x] 2.2 Document `TRAVEL_ENGINE_V2_ENABLED=false` in `.env.example` next to other v8.3 flags.

## 3. travel_rules constants

- [x] 3.1 Add normalizer constants (proximity meters, merge confidence threshold, and any tiny static alias pairs needed by fixtures) to `travel_rules.py` as module-level data.
- [x] 3.2 Add V2 scoring weights: diversity, geo fit, evidence, duplicate penalty. Keep existing `CATEGORY_WEIGHTS` and structural maps unchanged. If a weight would change golden preference outcomes, stop and add a golden case first (row 4.2 stop) instead of inventing a weight.

## 4. Candidate model + normalizer (4.1)

- [x] 4.1 Extend `PlaceCandidate` with optional defaults only: `user_selected`, `aliases`, `parent_place_id`, `source`, `source_id`, and evidence presence (`evidence_count` or opaque ref list). Legacy dicts with today's keys must still validate.
- [x] 4.2 Implement `src/travel_engine/candidate_normalizer.py`: name/category/coordinate comparison keys; exact-id, normalized-name+proximity, alias, parent/child dedup with confidence; user-selected retention; no aggressive merge of differently named nearby attractions. Pure; no `get_settings`, geo, HTTP, DB, or LLM imports.
- [x] 4.3 Expose a stable entry point (e.g. `normalize_candidates`) that is idempotent on survivor ids and keeps original display coords on survivors.

## 5. Evidence-aware scoring (4.2)

- [x] 5.1 Extend `score_place` / `select_places` with an injected `v2_enabled: bool = False` (and any pure context needed for geo-fit, e.g. optional base lat/lng). V2 off MUST match today's sum-of-matching-weights totals and interest breakdown keys.
- [x] 5.2 When `v2_enabled` is true, add configured diversity, geo fit, evidence, and dup-penalty terms into `score_breakdown`. Missing evidence ⇒ 0 for that term. Do not put `TRAVEL_ENGINE_V2_ENABLED` or `get_settings` in the engine package.
- [x] 5.3 Keep `explain_selection` as one compact string; ensure V2 breakdown keys appear when present. Prefer a shared pure helper (normalize-then-select) used by tools so call sites do not diverge.
- [x] 5.4 Update `_helpers.place_to_candidate` to map `Place.osm_id` into `source`/`source_id` when available without breaking existing callers.

## 6. Tool wiring

- [x] 6.1 Update `rank_places` to read `TRAVEL_ENGINE_V2_ENABLED` via `get_settings()`. Flag false ⇒ no normalizer, `v2_enabled=False`. Flag true ⇒ normalize then select with `v2_enabled=True`. Keep `ToolResult` keys unchanged.
- [x] 6.2 Update `build_route` auto-rank (empty `ranked_pois`) to use the same helper and flag gate. Do not change `allocate_days` / `optimize_route` behavior in this change.

## 7. Tests

- [x] 7.1 Add `tests/travel_engine/test_candidate_normalizer.py` covering: monastery name/alias variants collapse; adjacent distinct attractions both survive; exact-id collapse; user-selected retention; idempotent second pass; missing optional fields do not invent data; purity (no forbidden imports).
- [x] 7.2 Extend `tests/travel_engine/test_place_selector.py` (or sibling) for: legacy dict validation; V2-off byte-identical to current fixtures; V2-on breakdown keys; evidence-absent ⇒ 0; explanation includes a V2 term.
- [x] 7.3 Update `tests/travel_engine/test_properties.py`: implement `test_idempotent_dedup` against the normalizer; replace the “setting string absent because V2 does not exist” assertion with “engine sources contain neither `TRAVEL_ENGINE_V2_ENABLED` nor `get_settings`” plus injected-off equivalence.
- [x] 7.4 Add planner tool tests (or extend existing) proving `rank_places` and `build_route` auto-rank honor the flag the same way.

## 8. Verify and completion sync

- [x] 8.1 Run `pytest tests/travel_engine -k normalizer -v`, then `pytest tests/travel_engine -v`, then the planner tool tests touched above. All exit 0.
- [x] 8.2 Run `python scripts/run_evals.py --replay` with the flag off. Exit 0 / no new regressions. Do not flip the default to true.
- [x] 8.3 Run `pytest tests/architecture -v` (flag default false must stay green). Confirm `src/travel_engine/**` still passes purity / G2.
- [x] 8.4 Update `docs/context.md`: rows 4.1–4.2 done behind `TRAVEL_ENGINE_V2_ENABLED` (default false); next blueprint rows are 4.3+. Update `docs/v8.2/repository_audit.md` for `candidate_normalizer`, selector V2 terms, and the flag present/read by tools. Do not mark the full Slice 4 exit gate done.
- [x] 8.5 Confirm the diff stays inside task 1.2 paths. No Alembic, no `requirements.txt`, no FE/OpenAPI change, no `VALIDATOR_V2_ENFORCE`. Put the blueprint §19 completion report in the PR description.
