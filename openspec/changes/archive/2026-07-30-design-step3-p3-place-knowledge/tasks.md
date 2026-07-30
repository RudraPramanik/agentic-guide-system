## 1. Author hardened `docs/steps/step3.md` (v2)

- [x] 1.1 Replace `docs/steps/step3.md` with the v2 hardened P3 prompt (Fix Log + locked decisions + steps 3.0–3.6 + testing plan + checklist).
- [x] 1.2 Apply agreed nits in the prompt: drop obsolete `seed_destination` savepoint “backport” note; default `_qdrant_available = False` until ensure succeeds; document host `QDRANT_URL` as `http://localhost:6335` (compose `6335:6333`).
- [x] 1.3 Ensure build order is locked as `3.0 → 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6` with function-based availability, AsyncQdrantClient, `to_thread` encode, `begin_nested`, never `.limit(0)`, batch upsert, readiness wiring.
- [x] 1.4 Keep zero-happy-path validation commands and the expanded pytest plan (including distinct malformed-JSON and SAVEPOINT regression tests).
- [x] 1.5 Pre-implement plan fixes (no code): Step 3.6 readiness validation uses formula-correct fixtures (high fixture → `indexed_pct==0` only on Qdrant-down; gated fixture for non-ready tier); Step 3.1 notes existing `QDRANT_URL` default `6333`→`6335`; removed obsolete `docs/steps/step3_critic.md` (canonical prompt is `step3.md` only).

## 2. Align OpenSpec artifacts to v2 (this update)

- [x] 2.1 Proposal/design/specs reflect `enriched_tags`, async/function-flag contracts, scripts, and readiness — not v1 `Place.tags` overwrite / raw bool / sync client.
- [x] 2.2 Confirm no requirement invents new HTTP routes or planner tools for P3.
- [x] 2.3 Spec/design readiness scenarios match locked P2 score math (Qdrant-down zeros `indexed_pct`; non-ready tier only with gated fixtures).

## 3. Implement P3 from the hardened prompt (code — after prompt lands)

- [x] 3.1 Step 3.0 — migration `Place.enriched_tags` + model column.
- [x] 3.2 Step 3.1 — `src/search/client.py` AsyncQdrantClient + lifespan ensure/close + config keys; **fix existing `QDRANT_URL` default from `6333` → `6335`**.
- [x] 3.3 Step 3.2 — `src/search/embeddings.py` lifespan load + `to_thread` + parallel batch contract.
- [x] 3.4 Step 3.3 — `src/places/constants.py` + `PlaceService` enrich/parse split.
- [x] 3.5 Step 3.4 — `src/search/places_index.py` single/batch upsert, search, `count_indexed`.
- [x] 3.6 Step 3.5 — `scripts/enrich_places.py` + `scripts/index_places.py`.
- [x] 3.7 Step 3.6 — wire `DestinationService.get_readiness` to `is_qdrant_available()`; readiness tests use formula-correct fixtures (see step3.md / spec).
- [x] 3.8 Pytest plan from step3.md + P3 verification checklist; update `docs/context.md` when P3 is validated.
