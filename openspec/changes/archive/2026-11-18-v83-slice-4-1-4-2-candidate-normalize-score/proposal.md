## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 rows **4.1** and **4.2**, with candidate contracts in §6.4 and the flag in §7.1) is the next feature slice after Slice 3. There is no `docs/steps/step*.md` for these rows. `docs/context.md` names **Slice 4** as the next blueprint feature row. Duplicate monastery variants and name/proximity near-duplicates still reach ranking as separate stops, and scoring is still the v6.1 sum-of-matching-weights only. Rows 4.1–4.2 add a deterministic candidate normalizer and evidence-aware scoring behind `TRAVEL_ENGINE_V2_ENABLED` (default false) so generate stays byte-identical until an operator flips the kill-switch.

## What Changes

- Add pure `src/travel_engine/candidate_normalizer.py`: name/category/coordinate normalization; exact-ID, normalized-name, proximity, alias, and parent/child dedup with confidence; user-selected places retained; no aggressive merging of adjacent distinct attractions.
- Extend `place_selector` scoring: keep the v6.1 sum-of-matching-weights as the base; when V2 mode is on, add configured terms (diversity, geo fit, evidence, dup penalty) from `travel_rules.py`; fold those terms into `score_breakdown` and `explain_selection` strings for existing `tool_trace` (no new HTTP/SSE schema).
- Add `TRAVEL_ENGINE_V2_ENABLED` on `Settings` (default `false`) and document it in `.env.example`. The engine package stays pure: it receives an injected boolean / mode, and MUST NOT call `get_settings()` or embed the setting name.
- Wire the flag at the tool boundary: `rank_places` and the `build_route` auto-rank path normalize then score when the flag is on; when off, they call today's `select_places` only (no normalizer pass).
- Un-skip §11.6 idempotent-dedup property once the normalizer exists; replace the temporary “engine must not contain `TRAVEL_ENGINE_V2_ENABLED`” rule with flag-off equivalence to the v6.1 path.
- No **BREAKING** change to HTTP paths, SSE event names, GeoJSON, or flag-off ranked/selected output.

## Capabilities

### New Capabilities

- `travel-engine-candidate-normalizer`: pure candidate normalization and confidence-based dedup for travel-engine inputs.

### Modified Capabilities

- `travel-engine-place-selector`: additive optional candidate fields; V2 scoring terms behind an injected mode; flag-off scoring remains the current sum-of-weights path.
- `travel-engine-rules`: add V2 scoring / normalizer constants as data (weights, proximity, confidence thresholds). Existing structural and interest vocabularies stay.
- `travel-engine-properties`: enable idempotent-dedup against the normalizer; require flag-off / `v2=False` equivalence instead of forbidding a second engine path.
- `planner-discover-tools`: `rank_places` reads `TRAVEL_ENGINE_V2_ENABLED` via `get_settings()`, optionally normalizes, then selects with the matching mode.
- `planner-plan-replan-tools`: `build_route` auto-rank fallback uses the same flag-gated normalize + select path so PLAN cannot bypass V2 when DISCOVER skipped ranking.

## Impact

- **Work surface:** `guideagent` only. No frontend OpenSpec change and no parent-vault symptom (this is not auth/SSE/trips GeoJSON cross-boundary).
- **Code:** `src/travel_engine/candidate_normalizer.py` (new), `src/travel_engine/place_selector.py`, `src/travel_engine/travel_rules.py`, `src/planner/tools/rank_places.py`, `src/planner/tools/build_route.py`, `src/planner/tools/_helpers.py` (candidate mapping only), `src/config.py`, `.env.example`, `tests/travel_engine/**`, planner tool tests that assert flag-off identity.
- **Completion sync:** `docs/context.md` and the travel-engine / flag rows in `docs/v8.2/repository_audit.md` after verify commands pass. No other doc.
- **No new package.** No `requirements.txt` change. No Alembic revision. No HTTP/SSE contract change.
- **Evals:** `pytest tests/travel_engine` and `python scripts/run_evals.py --replay` must stay non-regressing with the flag off. Preference / duplicate golden cases that back V2 weights may be added under `evals/` only when they prove a weight; a weight change without golden evidence is a stop.

## Non-goals

- No rows **4.3–4.7** (allocator, optimizer, schedule, validator V2, replan mapping). `VALIDATOR_V2_ENFORCE` is not added or read.
- No rename of `PlaceCandidate.id` to `place_id`. Adapt the existing type; do not create a second candidate model.
- No aggressive merge of nearby distinct attractions; no LLM, no network, no DB inside `travel_engine/`.
- No FE contract, no OpenAPI change, no trip column, no SearchArea import into the engine.
- No Slice 5–9 work, no lodging, no media, no judge promotion.
- No rewrite of §9 in the blueprint. Checkout corrections stay in this change.
- The flag default stays false. Rollback is flag off (plus revert if needed).

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Keep `travel_engine/` free of I/O, `get_settings()`, geo, SQLAlchemy, HTTP, and LLM imports (G2 / purity).
- Read `TRAVEL_ENGINE_V2_ENABLED` only through `get_settings()` at the planner tool boundary (N2 kill-switch).
- Preserve flag-off ranked output identical to today's selector path (N1/N2).
- Keep explanations inside existing `tool_trace` / `ToolResult.data.explanations` — no schema change.
- Never invent authoritative IDs, coordinates, or prices from an LLM (N4). Dedup is deterministic.
- Treat missing evidence / alias / parent as unknown: score term contributes 0 or is skipped; never fabricate (N6).
- Stop if a proposed weight change is not backed by a golden preference / duplicate case (row 4.2 stop).

Checkout notes, confirmed against the tree rather than treated as a halt:

- `PlaceCandidate` uses `id`, not blueprint §6.4 `place_id`. Keep `id`. Optional additive fields (`source`, `source_id`, `aliases`, `parent_place_id`, `user_selected`, `evidence_refs` or equivalent) default empty so existing dicts still validate.
- `Place` has `osm_id` and `enriched_tags` but no alias/parent table. Alias and parent/child rules use optional fields on the candidate plus a small static alias map in `travel_rules` / normalizer data — not a new ORM relation.
- There is no `EvidenceRef` type in code. Evidence scoring uses optional structured refs or a count/presence term configured in `travel_rules`; absent evidence ⇒ 0, never a fake open/available claim.
- `src/config.py`, `.env.example`, and the two tool files sit outside the §9 path cells. The flag and generate wiring cannot live anywhere else. Same settings/wiring exception used for Slice 3.
- Property `test_engine_does_not_read_v2_flag` currently forbids the setting string inside `src/travel_engine/**`. Feature-proof replaces that with “engine source does not call `get_settings` / does not contain the setting name; tools inject a bool; `v2=False` matches legacy `select_places`.”
