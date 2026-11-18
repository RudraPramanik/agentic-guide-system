## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §8.2, §8.3, §9 rows **5.1–5.4**, §11.4) is the next product slice. This is not `docs/steps/step5.md` (P5 planner tools, already shipped). `docs/context.md` records Slices 1–4 as implemented behind flags, with the golden-case count still short of the Slice 2 minimum. Destination readiness is still the locked P2 count formula in `compute_readiness`: a destination can look fine because it has many places that all sit in one cluster. OSM `opening_hours` is stored on `places.tags` and is never parsed. `PlaceCandidate.opening_hours_status` stays `unknown`, so the schedule cannot use a verified window and nothing may claim a place is open. `retrieval_recall_at_k` exists as a pure function and is not a suite or a gate.

## What Changes

- Row **5.1**: add Readiness V2 as a pure function of place rows and requested `days`, behind `READINESS_V2_ENABLED` (default false). Flag off keeps today's `compute_readiness` result and the same `DestinationReadinessOut` fields. Flag on judges usable places after dedup and coordinate checks, category diversity, and multi-day geographic spread. Low readiness still warns. It does not block generation above `PLANNER_ABSOLUTE_MIN_PLACES`.
- Row **5.2**: add an endpoint-less ingestion report script. For Darjeeling, Manali, and Goa fixtures it prints counts, category distribution, duplicate rate, ingestion failures, and freshness. No HTTP route.
- Row **5.3**: parse a documented all-week subset of OSM `opening_hours` in `src/places/`, preserve the raw string, and set `verified` / `unknown` / `malformed` on the candidate the engine already consumes. No new package. Absent stays unknown. A weekday-only or seasonal rule stays unknown. Unrecognized text is malformed. Nothing in this slice claims "open now".
- Row **5.4**: add `run_evals.py --replay --suite retrieval`. It scores recorded top-k lists with the existing `retrieval_recall_at_k` and fails below 0.80 or below the frozen baseline. It does not call the planner, Qdrant, or a provider, and it does not change Darjeeling `score_case` verdicts.
- No **BREAKING** change to HTTP paths, response fields, SSE event names, GeoJSON, the P2 formula when the flag is off, or finding codes.

## Capabilities

### New Capabilities

- `destination-ingestion-report`: fixture-backed, endpoint-less per-destination ingestion quality report (row 5.2).
- `place-opening-hours`: pure OSM hours parser and the flag-gated mapping onto `PlaceCandidate` (row 5.3).

### Modified Capabilities

- `destination-readiness`: V2 tier rules behind the flag; the P2 `compute_readiness` contract stays the flag-off path (row 5.1).
- `destinations-http`: optional `days` query on the existing readiness route; response model unchanged; flag off matches today's body.
- `planner-discover-tools`: `check_readiness` forwards the trip's `days` and still only warns.
- `travel-engine-place-selector`: optional `opening_hours_raw` on `PlaceCandidate`; scoring ignores hours; the module still does not parse OSM text.
- `eval-golden-harness`: a retrieval suite, parallel to the location suite, that the default itinerary loader does not read (row 5.4).

## Impact

- **Work surface:** `guideagent` only. No frontend change and no parent-vault symptom.
- **Code:** `src/destinations/readiness.py`, `src/destinations/service.py`, `src/destinations/router.py` (optional query only), `src/config.py`, `.env.example`, `src/places/repository.py` (unpaginated read for the scorer), `src/places/opening_hours.py`, `src/planner/tools/_helpers.py`, `src/planner/tools/check_readiness.py`, `src/planner/service.py` (days into the pre-graph readiness read), `src/trips/service.py` (same hours mapping when a trip edit rebuilds a candidate), `src/travel_engine/place_selector.py` (optional raw field only), `scripts/ingestion_report.py`, `scripts/run_evals.py`, `src/evaluation/retrieval_suite.py`, `evals/golden/retrieval/**`, `evals/fixtures/ingestion/**`, `evals/baselines/retrieval.json`.
- **Tests:** `tests/destinations`, `tests/places`, `tests/travel_engine`, `tests/evaluation`.
- **Settings added, all with legacy defaults:** `READINESS_V2_ENABLED=false`, `READINESS_MIN_USABLE_PLACES_PER_DAY=4`, `READINESS_MIN_CATEGORIES=3`, `READINESS_MIN_CLUSTERS_MULTI_DAY=2`.
- **No new package, no Alembic revision, no new finding code, no new HTTP path.** Raw hours stay in the existing `places.tags` JSON. `PLANNER_ABSOLUTE_MIN_PLACES` stays the pre-graph 409 floor.
- **Status note:** `docs/context.md` names golden-case expansion as the first open Slice 1–4 gap. This change does not close that gap and does not claim the Slice 4 exit gate.

## Non-goals

- No rewrite of the P2 formula, and no change to its results when `READINESS_V2_ENABLED` is false.
- No readiness HTTP field added or removed. Tier stays `ready | limited | sparse`.
- No blocking of generate on `limited` or `sparse` when `place_count` is already at the absolute floor.
- No ingestion HTTP endpoint, dashboard, or live Overpass call inside the report script.
- No full OSM opening_hours grammar, no sunrise/sunset, no public-holiday or month rules, no timezone, and no date-specific schedule (§8.4 stays deferred).
- No "open now" string in API copy, validator messages, or schedule notes.
- No new `ValidationFinding` code. Malformed and unknown hours keep today's info finding `OPENING_HOURS_UNKNOWN`. Only a verified window can raise `OPENING_HOURS_CONFLICT`.
- No change to `score_case`, Darjeeling assertion keys, or the requirement that the itinerary replay stay flag-off and byte-stable.
- No live Qdrant recall on the PR gate. Recorded rankings only.
- No flip of `READINESS_V2_ENABLED`, `TRAVEL_ENGINE_V2_ENABLED`, or `VALIDATOR_V2_ENFORCE` defaults.
- No Slice 6–9 work and no edit of blueprint §9 inside this change.

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Keep `compute_readiness` and the new V2 function pure: no SQLAlchemy, HTTP, Qdrant, or LLM (existing destination-readiness spec).
- Read `READINESS_V2_ENABLED` only through `get_settings()` at the service and tool boundary (N2, G3, G11). The travel engine must not read the flag. It only sees `opening_hours_status` plus open/close strings.
- Leave unknown hours unknown. Do not default a missing or weekday-limited string to open (N4, N6).
- Keep the public readiness envelope and the 409 floor (row 5.1 stop line is an envelope change).
- Add a parser dependency only if a bounded in-repo grammar cannot meet the tests. A heavy package is a stop, not a silent add (row 5.3, G9).
- Keep flag-off generate and flag-off readiness identical to today (G13).
