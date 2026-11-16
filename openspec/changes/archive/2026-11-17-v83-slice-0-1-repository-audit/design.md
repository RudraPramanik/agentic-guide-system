## Context

See proposal.md — Why. The checkout is post-P7 / v7: `docs/context.md` marks P0–P7 and V0–V6.1 done, and V6.2/V6.3 deferred. Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md`) is the target plan. Its §5.3 modules (`location_intelligence/`, `planner/runs/`, `geo/media/`) and its §7 flags are proposed. Subslice 0.1 may write only `docs/v8.2/**`. This change adds no external I/O, so there is no new timeout, retry, or fallback. The audit records the resilience already on geo and LLM calls; it does not add any. `travel_engine/` stays a pure-Python classification target, not a place this change edits.

## Goals / Non-Goals

**Goals:**

- One audit file later slices can cite by heading.
- Every status row is checkable: path, symbol, test, or an explicit "no test".
- Proposed v8 names are listed as absent unless a symbol link proves otherwise.
- Contradictions stay in the audit and do not stop the rest of the matrix.

**Non-Goals:**

- Rewriting the blueprint, filling `[SET IN S0]`, or writing ADR-001–ADR-004.
- Running or repairing the pytest suite (that gate is 0.2).
- Copying v6.1 or v7 contracts into the audit. Link the section and record present or absent.

## Decisions

### 1. One file, fixed headings

Write only `docs/v8.2/repository_audit.md`, with these headings in order:

1. Status matrix
2. Settings inventory
3. SSE lifecycle
4. FE map and guide integration
5. Display-only stays and photos
6. Proposed v8 surface
7. Contradiction log

Alternative considered: one file per slice. Rejected. 0.1 names a single deliverable, and split files would invite edits outside a later subslice's mental model while still sitting in `docs/v8.2/**`.

### 2. Status vocabulary and evidence

Each matrix row uses exactly one of: `implemented-tested`, `implemented-untested`, `partial`, `stub`, `deferred`.

| Status | Use when |
|---|---|
| `implemented-tested` | Symbol exists and a test file asserts it |
| `implemented-untested` | Symbol exists; test cell is `no test` |
| `partial` | Symbol exists and a named part of the blueprint contract is missing |
| `stub` | File or symbol exists and its body is a placeholder |
| `deferred` | Blueprint names it and the checkout has no symbol |

A row without a path is invalid. `docs/context.md` is not evidence. A test link is a file path plus the test name when one exists.

Minimum rows, grouped so later slices can find them:

- Inherited runtime: settings, LLM gateway (`src/core/llm/client.py`), geo gateways, places, destinations and readiness, search/Qdrant, each `travel_engine` module, planner graph and tools, trips (save, GeoJSON, edits), evaluation harness and scorers, guest ownership (`wandr_session`).
- Leftover packages still on disk (confirm `src/app/` and `src/evalution/` if present) get their own rows rather than being folded into the real packages.
- Proposed surface: one row per §7.1 flag, each §7.2 setting name, each §8.1 table or column, `location_intelligence/`, `planner/runs/`, `geo/media/`, lodging-as-place, and `places.media`. Default status `deferred` until a symbol is found.

### 3. Settings inventory is a three-way diff

Columns: name, where it lives (`Settings`, `.env.example`, both, or blueprint-only), default if the field exists, slice that proposes it or `shipped`.

Blueprint-only names (`RUN_TRACKING_ENABLED`, `LOCATION_V2_ENABLED`, `TRAVEL_ENGINE_V2_ENABLED`, `VALIDATOR_V2_ENFORCE`, `READINESS_V2_ENABLED`, `CANONICAL_TRIP_V2_ENABLED`, `REASONING_LAYER_ENABLED`, `REASONING_SHADOW_SAMPLE_RATE`, `EVALUATION_JUDGE_ENABLED`, `LODGING_V1_ENABLED`, `MEDIA_ENRICH_ENABLED`, and the §7.2 knobs) stay blueprint-only unless `src/config.py` defines them. Do not add them to `.env.example` in this subslice.

### 4. SSE lifecycle is taken from emitters

Source of truth is the code that yields frames: `src/planner/router.py` (`TERMINAL_EVENTS`, `sse_frame`), `src/planner/service.py`, `src/planner/emit_terminals.py`. `docs/FE_guide.md` §7 is the contract to compare. Columns: event name, progress or terminal, emitter symbol, pre-stream HTTP (the 409 floor) called out separately from SSE. A name that appears only in the guide, or only in code, is a contradiction-log row.

### 5. FE map and guide is a read of the sibling repo

Read `guideagent-frontend` and cite paths. Do not edit that repo, and do not copy component source into the audit. Start from `features/trips/trip-map.tsx`, `features/trips/trip-detail.tsx`, `features/trips/trip-page.tsx`, and `docs/FE_guide.md` §15 (GeoJSON). Record whether a distinct guide-agent UI exists. If the only "guide" is planner progress plus the trip page, say that, with the files checked.

### 6. Display-only stays and photos are their own section

Required rows, each with a path:

- `accommodation_label` on `PlanRequest` (`src/planner/schemas.py`) and where the router echoes it.
- The trip-page string `Stays are unavailable.` (`guideagent-frontend/features/trips/trip-page.tsx`).
- Stop card rendering. The blueprint says "gradient stop cards". That phrase is a claim. Record the component and the classes it actually uses. A mismatch is a contradiction-log entry, and the section still describes the real card.

Also record that `Place` has no media field unless the model proves otherwise, and that no lodging table exists unless a model proves otherwise. Slice 9 must be able to read this section and see that these surfaces are not photos and not stay suggestions.

### 7. Contradictions are logged, then the audit continues

The log columns are: blueprint section, claim, what the checkout shows, path. Subslice 0.1 does not write ADR files and does not stop after the first mismatch. §18 item 1 applies to later subslices that would change behavior. Empty log is allowed if nothing disagreed.

### 8. Verify by reading the links, not by pytest

Done means: every matrix row has a path and a symbol or `no test`; every §7.1 flag appears in the settings inventory; the four display-only rows exist; the contradiction log heading exists. Rollback is deleting `docs/v8.2/`. No flag, because nothing in the request path changes.

## Risks / Trade-offs

- [Audit grows into a second blueprint] → Status, links, and one-line notes only. No proposed algorithms.
- [A progress row in `docs/context.md` is copied as proof] → Evidence rule rejects it. The row needs a source path.
- [A contradiction tempts a code fix] → Log it. Allowed paths forbid the fix. 0.5 explicitly does not fix unrelated violations.
- [Sibling frontend moves] → Cite repo-relative paths and the date of the read. Do not vendor snippets.
- [A proposed flag is already present under another name] → Inventory the existing name in the shipped column and point the blueprint name at it in the contradiction log. Do not rename it here.

## Migration Plan

No deploy, migration, or flag. Rollback is deleting `docs/v8.2/repository_audit.md` (and `docs/v8.2/` if that was the only file).

## Open Questions

None. Whether stop cards are gradients is an audit finding under Decision 6, not a choice that changes the file outline or the tasks.
