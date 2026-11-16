## 1. Preflight

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §9 row 0.1, and this change's `design.md`. List the files that will be read. The only write is `docs/v8.2/repository_audit.md`.
- [x] 1.2 Confirm the worktree has no edits outside `docs/v8.2/**` before drafting. Do not run the suite and do not fix code (suite health is subslice 0.2).

## 2. Audit skeleton

- [x] 2.1 Create `docs/v8.2/repository_audit.md` with the seven headings from design Decision 1, in that order, plus a one-line note of the read date. Status vocabulary matches Decision 2.

## 3. Status matrix

- [x] 3.1 Fill inherited-runtime rows for settings, `src/core/llm/client.py`, geo gateways, places, destinations and readiness, and search/Qdrant. Each row has a path, a symbol, and a test path or `no test`.
- [x] 3.2 Fill rows for each `travel_engine` module (protocols, rules, place selector, day allocator, route optimizer, schedule builder, trip validator). Note purity from imports only. Do not change those files.
- [x] 3.3 Fill rows for the planner graph and tools, SSE generate, trips save / GeoJSON / edits, evaluation harness and scorers, and guest ownership via `wandr_session`.
- [x] 3.4 Classify leftover packages still on disk, including `src/app/` and `src/evalution/` if they exist, as their own rows (`stub` or whatever the files show). Do not fold them into the real packages.

## 4. Settings inventory

- [x] 4.1 Diff `Settings` in `src/config.py` against `.env.example`. Columns: name, where it lives, default when the field exists, `shipped` or the proposing slice.
- [x] 4.2 Add every §7.1 flag and every §7.2 setting name. Mark each `blueprint-only` unless `src/config.py` already defines it. Do not edit `.env.example` or `src/config.py`.

## 5. SSE lifecycle

- [x] 5.1 Build the event table from `src/planner/router.py`, `src/planner/service.py`, and `src/planner/emit_terminals.py`. Compare names with `docs/FE_guide.md` §7. Columns: event, progress or terminal, emitter symbol.
- [x] 5.2 Record the pre-stream HTTP 409 floor (`destination_not_ready`) on its own row, separate from SSE frames. Names that exist only in the guide or only in code go to the contradiction log.

## 6. FE map and guide

- [x] 6.1 Read `guideagent-frontend/features/trips/trip-map.tsx`, `trip-detail.tsx`, `trip-page.tsx`, and `docs/FE_guide.md` §15. Cite those paths. Do not edit the frontend repo and do not paste component source.
- [x] 6.2 Record whether a distinct guide-agent UI exists. If the only guide surface is planner progress plus the trip page, say that and list the files checked.

## 7. Display-only stays and photos

- [x] 7.1 Record `accommodation_label` on `PlanRequest` (`src/planner/schemas.py`) and the router echo site.
- [x] 7.2 Record the trip-page copy `Stays are unavailable.` with its frontend path.
- [x] 7.3 Record the stop-card component and the classes it uses. Treat "gradient stop cards" as a claim to check. A mismatch is a contradiction-log row; the section still describes the real card.
- [x] 7.4 Record whether `Place` has a media field and whether a lodging table exists, with the model file as evidence. Default is absent.

## 8. Proposed v8 surface

- [x] 8.1 Add rows for `location_intelligence/`, `planner/runs/`, `src/geo/media/`, and each §8.1 table or column (`planner_runs`, trip `search_area` / `discovery_anchor`, stop status, `trips.version`, feedback table, `places.media`, lodging rows). Status `deferred` unless a symbol link proves otherwise.

## 9. Contradiction log and verify

- [x] 9.1 Fill the contradiction log (blueprint section, claim, checkout, path). An empty disagreement list is valid; the heading and columns must exist. Do not write ADR files.
- [x] 9.2 Link check: every matrix row has a path and a symbol or `no test`; every §7.1 flag appears in the settings inventory; the display-only section has the label, the stay copy, the real stop card, and the media/lodging absence-or-presence note.
- [x] 9.3 Confirm the diff is only `docs/v8.2/repository_audit.md`. Leave `docs/context.md` unchanged: subslice 0.1's allowed paths forbid it (proposal Constraints). Put the §19 completion report in the PR description, not in a new file.
