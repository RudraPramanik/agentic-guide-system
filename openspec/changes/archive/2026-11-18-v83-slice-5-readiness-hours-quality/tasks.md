## 1. Settings

- [x] 1.1 Add `READINESS_V2_ENABLED=false`, `READINESS_MIN_USABLE_PLACES_PER_DAY=4`, `READINESS_MIN_CATEGORIES=3`, and `READINESS_MIN_CLUSTERS_MULTI_DAY=2` to `src/config.py` and `.env.example`. Defaults stay legacy. No other setting changes.
- [x] 1.2 Confirm the architecture flag test still expects `READINESS_V2_ENABLED` false once the field exists. Run `pytest tests/architecture -k flag -q` or the closest existing settings-default test.

## 2. Readiness V2 (row 5.1)

- [x] 2.1 Add pure `compute_readiness_v2` in `src/destinations/readiness.py` with the usable-place, dedup, 10 km single-linkage, score-band, and message rules in `design.md`. Leave `compute_readiness` unchanged. Do not import the database, HTTP, Qdrant, or `travel_engine`.
- [x] 2.2 Add unit tests: ten clustered places are `limited` for 3 days; twelve places in two clusters are `ready` for 3 days; nine places are `sparse`; one null-island coordinate blocks `ready`; same name within 100 m counts once; a 70 percent cluster passes and a larger share fails; evidence share does not change a `ready` message; the 150 m and 10 km constants equal `NORMALIZER_PROXIMITY_M` and `CLUSTER_RADIUS_KM`.
- [x] 2.3 Add `PlaceRepository.list_all_for_destination` (non-deleted, no page cap). `DestinationService.get_readiness(destination_id, days=1)` uses the P2 function and does not call it when the flag is false, and uses V2 with that list when the flag is true. Database errors propagate. `place_count` on the V2 result is the usable count; `enriched_pct` and `indexed_pct` stay the counter ratios.
- [x] 2.4 Add optional `days` (`ge=1`, `le=30`, default 1) on `GET /api/v1/destinations/{id}/readiness`. Out of range returns 422. Response fields stay `destination_id`, `score`, `tier`, `place_count`, `enriched_pct`, `indexed_pct`, `message`. Flag off: `days=3` and omitted `days` return the same body as today.
- [x] 2.5 Pass generate `days` from `_bind_known_destination` and `check_readiness`. Omitted generate `days` passes 3. A score under `PLANNER_MIN_READINESS_SCORE` still returns `ok=True` with a warning. Flag off: day count does not change the stored score. Tool result keys stay the current set.

## 3. Ingestion report (row 5.2)

- [x] 3.1 Add synthetic fixtures `evals/fixtures/ingestion/darjeeling.json`, `manali.json`, and `goa.json` with `as_of`, places, and failures. Include one same-name pair 100 m apart and one stale or missing timestamp so the rates are hand-checkable. State in the fixture or script docstring that these are samples, not a live catalog dump.
- [x] 3.2 Add `scripts/ingestion_report.py`. It prints one JSON document (count, category map, duplicate rate via the readiness dedup helper, failure count and reasons, freshness against fixture `as_of`) and exits 0. It does not open a database or the network. A missing fixture exits non-zero and names the destination.
- [x] 3.3 Test the known duplicate rate 0.5, the stale freshness share, echoed failure reasons, and the missing-fixture failure.

## 4. Opening hours (row 5.3)

- [x] 4.1 Add `parse_opening_hours` in `src/places/opening_hours.py` for the exact grammar in the place-opening-hours spec. No new package and no `requirements.txt` change. Tests: null and whitespace are `unknown`; `Mo-Su 09:00-17:00` and `24/7` are `verified`; `off` is verified `00:00`–`00:00`; `Mo-Fr 09:00-17:00` is `unknown` with raw kept; `every morning` is `malformed` with raw kept.
- [x] 4.2 Add optional `opening_hours_raw` on `PlaceCandidate` (default null). Scoring ignores hours fields. `src/travel_engine/**` does not import the parser or read `READINESS_V2_ENABLED`.
- [x] 4.3 When the flag is true, `place_to_candidate` and both trip-edit `PlaceCandidate` constructors apply the parser to `tags["opening_hours"]`. When the flag is false, status stays `unknown` and open, close, and raw stay null even if the tag is present.
- [x] 4.4 Engine tests: `malformed` and `unknown` produce no note that says the place is open and do not raise `OPENING_HOURS_CONFLICT`; a verified empty window is not placed as an open visit; a verified window that cannot hold the visit is omitted from the V2 schedule.

## 5. Retrieval gate (row 5.4)

- [x] 5.1 Add `src/evaluation/retrieval_suite.py` and `evals/golden/retrieval/*.json`. Cases call `retrieval_recall_at_k` at k 10. Do not change that function. Include one checked-in case at recall 1.0 and one at exactly 0.80. Keep a 0.5 case in the unit test only.
- [x] 5.2 Teach `scripts/run_evals.py --suite retrieval` to score that folder only. `--replay` on it must not call the planner, a provider, Qdrant, or a database. The default replay must still load only `evals/golden/darjeeling`. A case below 0.80, or a mean below `evals/baselines/retrieval.json`, exits non-zero and the low-baseline output contains `retrieval_recall@10`. `--update-baseline` writes only that retrieval baseline.
- [x] 5.3 Commit `evals/baselines/retrieval.json` at the mean of the checked-in cases. Assert an existing Darjeeling `score_case` verdict is unchanged.

## 6. Proof

- [x] 6.1 Run `pytest tests/destinations tests/places tests/travel_engine tests/evaluation -q` and `python scripts/ingestion_report.py`. All green.
- [x] 6.2 Run `python scripts/run_evals.py --replay --suite retrieval` and `python scripts/run_evals.py --replay`. Retrieval exits 0. The Darjeeling replay stays flag-off and does not regress.
- [x] 6.3 Update `docs/context.md` and the readiness / hours rows in `docs/v8.2/repository_audit.md`: Slice 5 is implemented behind `READINESS_V2_ENABLED` (default false). Do not claim the Slice 2 case-count gap or the Slice 4 exit gate is closed.
