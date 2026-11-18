## Context

See `proposal.md` for why this slice exists. The code that shapes the approach:

- `compute_readiness` in `src/destinations/readiness.py` is pure and takes four counters. `DestinationService.get_readiness` calls it with denormalized counters and `is_qdrant_available()`. The HTTP body is `DestinationReadinessOut` (`score`, `tier`, `place_count`, `enriched_pct`, `indexed_pct`, `message`).
- `PlaceRepository.list_by_destination` is paginated. Readiness V2 needs every non-deleted place for one destination.
- OSM tags already land on `places.tags`. The opening-hours string, when Overpass sent one, is `tags["opening_hours"]`. There is no parsed column.
- `PlaceCandidate` already has `opening_hours_status`, `opening_open`, and `opening_close`. Schedule V2 and the validator already consume them. `place_to_candidate` in `src/planner/tools/_helpers.py` does not set them, so they stay `unknown`. Trip edits build their own `PlaceCandidate` values in `src/trips/service.py`.
- `retrieval_recall_at_k` in `src/evaluation/metrics/__init__.py` is the recall formula. `scripts/run_evals.py --suite` currently accepts only `location`. The default replay loads `evals/golden/darjeeling` only.
- Generate's pre-graph hook `_bind_known_destination` stores `readiness_score` before the graph. `GenerateIn.days` is optional. `parse_preferences` defaults a missing day count to 3.

No new external call is added. Resilience contracts (timeout, retry, named fallback) are unchanged. The new database read is the existing place table on the request session.

## Goals / Non-Goals

**Goals:**

- One flag, default false, restores today's readiness score and leaves hours `unknown`.
- V2 tier bands stay on the same 0.3 and 0.7 cuts the HTTP client and `PLANNER_MIN_READINESS_SCORE` already use.
- The hours parser is the only new grammar, and the engine never sees the raw string as authority.
- The retrieval gate fails in CI on a recorded list, with a hand-checked 0.80 case in the passing set.

**Non-Goals:**

- See `proposal.md`. In particular this design does not extend parent/child or alias dedup into readiness, and it does not add a weekday calendar to the schedule.

## Decisions

### 1. Flag and settings live on `Settings`

Add `READINESS_V2_ENABLED: bool = False`, `READINESS_MIN_USABLE_PLACES_PER_DAY: int = 4`, `READINESS_MIN_CATEGORIES: int = 3`, `READINESS_MIN_CLUSTERS_MULTI_DAY: int = 2` in `src/config.py`, and the same keys in `.env.example`. Call `get_settings()` only in `DestinationService`, `check_readiness`, `_bind_known_destination`, and the place-to-candidate mapper. The destinations router forwards `days` and does not branch on the flag. `src/travel_engine/**` must not mention the flag.

Alternative considered: a second flag for hours. Rejected. Row 5.3's rollback is the slice flag, and hours must stay dark when readiness stays dark.

### 2. V2 is a second pure function, not a rewrite of `compute_readiness`

Keep `compute_readiness` byte-identical. Add `compute_readiness_v2(places, days, thresholds) -> ReadinessResult` beside it. The service picks the function. Flag off must not query places.

`days` on the service defaults to 1 so the catalog route and a direct call stay single-day. Generate does not use that default. `_bind_known_destination` and `check_readiness` pass `GenerateIn.days` when it is set, and pass 3 when it is omitted, matching `_DEFAULT_DAYS` in `parse_preferences`. The catalog route defaults `?days` to 1 because that request is not a trip. Both paths clamp to 1..30; 422 only on the HTTP query.

Alternative considered: always pass 1 when the client omits days. Rejected. The planner would still build a 3-day trip, and the score on state would describe a shorter trip than the one published.

### 3. Usable set, clusters, and score

Inputs to the pure function are plain values (`id`, `name`, `category`, `lat`, `lng`, `source`, `retrieved_at`). The service extracts lat/lng with the existing geometry helper and passes `created_at` as the retrieval timestamp. No geometry library inside `readiness.py`.

Dedup, in order: drop invalid coordinates (non-finite, outside range, or exactly 0,0) but remember that an invalid coordinate was seen; collapse equal ids; collapse equal names within 150 meters. Name key is case-fold, trim, and strip punctuation. This is narrower than `normalize_candidates`. Parent/child and alias merges stay in the engine. A monastery and a viewpoint 100 meters apart with different names both count. The 150 meter and 10 kilometer figures must match `NORMALIZER_PROXIMITY_M` and `CLUSTER_RADIUS_KM`. A unit test imports both sides and asserts the numbers. Readiness does not import `travel_engine` at runtime.

Clusters: sort by id, single-linkage, join the first group that has any member within 10 km, otherwise start a group. Largest share uses the usable count after dedup. `>` 0.70 fails. `==` 0.70 passes. Day count 1 skips this check.

Coordinate check fails if any input row was invalid, even though that row is not usable.

Score, so the tier bands stay testable:

- sparse (`usable < 10`): `round(min(0.299, usable / 10 * 0.299), 3)`
- limited: `round(min(0.699, 0.300 + 0.399 * worst_ratio), 3)` where `worst_ratio` is the minimum of the count ratio, the category ratio, and, when days > 1, the spread ratio. A failed coordinate check forces `worst_ratio` to 0, so the score is 0.300. The result is clamped into `[0.300, 0.699]`.
- ready: `1.0`, message `None`

Evidence share is `(usable places with non-empty source and a timestamp) / usable`, or 1 when usable is 0. It is appended to the limited or sparse message when it is below 1. It does not change a ready message or any tier.

`place_count` in the V2 DTO is the usable count. `enriched_pct` and `indexed_pct` stay the counter ratios from the destination row, so the flag-off HTTP fixture and the flag-on percentages stay comparable.

Alternative considered: a new response field for evidence and cluster counts. Rejected. Row 5.1 stops on an envelope change.

### 4. Place load is one repository method

Add `PlaceRepository.list_all_for_destination(destination_id)` returning non-deleted rows, no page cap. The service calls it only when the flag is on. Do not loop `list_by_destination`. A database error propagates. Do not catch it and silently score with the P2 formula while the flag is on. Rollback is the flag.

### 5. Hours grammar stays in `src/places/opening_hours.py`

`parse_opening_hours(raw) -> ParsedHours` with `status`, `raw`, `opening_open`, `opening_close`.

Exact verified forms, after trim, case-sensitive except the closed words:

- `24/7` → `00:00`–`24:00`
- `Mo-Su HH:MM-HH:MM` with close later than open, hours 00–23, minutes 00–59, close allowed to be `24:00`
- `off` or `closed` → verified `00:00`–`00:00` (empty window, not an open interval)

Unknown, raw kept, times null, when the string is not verified and it names a restricted weekday, a month, `PH`, `SH`, sunrise, sunset, dawn, or dusk. Everything else non-empty is malformed. No fuzzy spaces. `Mo-Su 09:00-17:00; PH off` is unknown because of `PH`, not verified.

`apply_hours(candidate, tags, enabled)` returns the candidate unchanged when `enabled` is false. When true, it reads `tags["opening_hours"]` if that value is a string. `place_to_candidate` and both `PlaceCandidate(...)` sites in `src/trips/service.py` call it. The engine does not import this module.

`opening_hours_raw` is an optional field on `PlaceCandidate`, default null. Scoring ignores it. `24:00` already parses in the schedule and finding helpers (`int(hours) * 60`).

No package. If a later destination needs the full OSM grammar, that is an ADR and a stop, not a silent dependency.

### 6. Ingestion report is fixture JSON, not a live audit

`scripts/ingestion_report.py` reads `evals/fixtures/ingestion/darjeeling.json`, `manali.json`, and `goa.json`. Each file is `{ "destination", "as_of", "places": [...], "failures": [...] }`. Places carry `id`, `name`, `category`, `lat`, `lng`, `retrieved_at`. Failures are `{ "reason" }` and are copied, not inferred. The script prints one JSON object and exits 0 or non-zero as the spec says. It shares the dedup rules with readiness by calling the same pure helper, so the duplicate rate cannot drift. These fixtures are synthetic and are not described as an OSM dump.

### 7. Retrieval suite follows the location-suite shape

`src/evaluation/retrieval_suite.py` loads `evals/golden/retrieval/*.json`. Each case is `{ "id", "retrieved": [ids in rank order], "must_include": [ids] }`. Score with `retrieval_recall_at_k(..., k=10)`. `run_evals.py --suite` gains `retrieval` next to `location`. The default destination run does not see that folder.

Checked-in cases include one recall of 1.0 and one of exactly 0.80 (four of five labels in the first ten). A 0.5 case belongs in the unit test that feeds the suite function a temporary file, not in the folder the CI command scores. Commit `evals/baselines/retrieval.json` with the mean of the checked-in cases so the first green run is reproducible. `--update-baseline` rewrites that file and nothing under `evals/baselines/` for other destinations.

The metric function is not edited.

### 8. Blueprint path cells versus wiring

Rows 5.1–5.4 name the modules that own the behavior. This change also touches the seams that already call those modules. That is the same wiring exception used in Slices 3 and 4, recorded here so apply does not treat it as scope creep:

- `src/config.py`, `.env.example` (the flag does not exist until it is declared)
- `src/destinations/router.py` (optional `days` only)
- `src/places/repository.py` (the unpaginated read)
- `src/planner/tools/_helpers.py`, `src/planner/tools/check_readiness.py`, `src/planner/service.py`
- `src/trips/service.py` (the two candidate constructors)
- `src/travel_engine/place_selector.py` (the optional raw field only)
- tests, `docs/context.md`, and `docs/v8.2/repository_audit.md` status rows after the code lands

No router-to-repository shortcut. No Alembic revision.

## Risks / Trade-offs

- [V2 loads every place for a destination on each readiness call] → Flag off skips the query. Flag on is one filtered select, not a page loop. Generate already reads the destination row.
- [A weekday string marked verified would schedule Saturday as if it were Monday] → Only `Mo-Su` and `24/7` become an open window. Restricted weekdays stay `unknown`.
- [`off` as `00:00`–`00:00` could be misread as "open at midnight"] → Schedule V2 places a visit only when the window contains it. An empty window cannot. Findings raise `OPENING_HOURS_CONFLICT` only for a real interval that the stop misses. Tests cover the empty window.
- [Flag-on scores change `readiness_score` on generate] → Replay and snapshots run with the flag false. Do not turn the flag on in `evals/` or `.env.example`.
- [Readiness dedup is narrower than the candidate normalizer, so the catalog can count two aliases the engine would merge] → Accepted. Readiness is a supply check. The engine still merges at selection time. The message does not claim the count is the post-normalizer stop count.
- [Retrieval recall does not execute Qdrant] → The PR gate stays replayable. A nightly live recall is out of this slice. The suite still fails if the metric or the labeled lists regress.
- [Synthetic ingestion fixtures can be mistaken for catalog health] → The script docstring and the fixture `destination` notes say they are checked-in samples. The script has no database DSN argument.

## Migration Plan

1. Ship with `READINESS_V2_ENABLED=false`. Flag-off readiness tests and the Darjeeling replay must match current scores.
2. Operators turn the flag on per environment after `pytest tests/destinations tests/places tests/travel_engine` and `python scripts/run_evals.py --replay --suite retrieval` are green.
3. Rollback is the flag back to false. The retrieval suite and the report script are reverted by reverting the change; they are not on the request path.
4. No migration to apply or roll back. Parsed hours are not stored.

## Open Questions

None. The day-count split (catalog default 1, generate default 3), the dedup width, the hours grammar, and the recorded retrieval gate are decided above and in the delta specs.
