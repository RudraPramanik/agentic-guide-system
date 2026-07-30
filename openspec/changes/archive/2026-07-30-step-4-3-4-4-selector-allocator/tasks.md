## 1. Step 4.3 — place_selector

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step4.md` step 4.3 (plus design D2–D4) before coding
- [x] 1.2 Implement `PlaceCandidate`, `TripPreferences`, `ScoredPlace` in `src/travel_engine/place_selector.py` (Pydantic or dataclasses; no SQLAlchemy Place)
- [x] 1.3 Implement `score_place` (sum formula), `explain_selection` (compact string), and `select_places` (sort + greedy AVOID_SAME_DAY_PAIRS keep-higher-score; budget soft-only); document greedy rule in module docstring
- [x] 1.4 Run step 4.3 ✅ validation snippet from `docs/steps/step4.md`
- [x] 1.5 Confirm no `src.geo` / httpx / litellm / qdrant / sqlalchemy imports in `place_selector.py`

## 2. Step 4.3 — selector tests

- [x] 2.1 Create `tests/travel_engine/test_place_selector.py`
- [x] 2.2 Cover: multi-interest score > single-interest; empty `enriched_tags` → score 0 still returned; empty candidates → `[]`; empty interests → all scores 0
- [x] 2.3 Cover: two monasteries + `AVOID_SAME_DAY_PAIRS` → lower-scored dropped; unknown tags do not KeyError
- [x] 2.4 Cover: `explain_selection` includes name and breakdown; stable sort tie-break sanity
- [x] 2.5 Run `python -m pytest tests/travel_engine/test_place_selector.py -v`

## 3. Step 4.4 — day_allocator

- [x] 3.1 Re-read `docs/steps/step4.md` step 4.4 and design D5 before coding
- [x] 3.2 Implement local haversine helper + `allocate_days` in `src/travel_engine/day_allocator.py` (cluster-first, caps, visit budget via `visit_duration_min`; omit overflow; docstring notes omission)
- [x] 3.3 Raise `ValueError("days must be >= 1")` when `days < 1`
- [x] 3.4 Run step 4.4 ✅ validation snippet (18 places / 3 days)
- [x] 3.5 Confirm no `src.geo` / httpx imports in `day_allocator.py`

## 4. Step 4.4 — allocator tests

- [x] 4.1 Create `tests/travel_engine/test_day_allocator.py`
- [x] 4.2 Cover: 18 places / 3 days → 3 lists, each ≤6, visit sum ≤ `ACTIVE_DAY_VISIT_BUDGET_MIN`
- [x] 4.3 Cover: `days=0` → `ValueError`; never >6 places on a day; trailhead-heavy set still respects visit budget
- [x] 4.4 Cover: two nearby + one far place prefer same-day clustering for the nearby pair when capacity allows
- [x] 4.5 Run `python -m pytest tests/travel_engine/test_day_allocator.py -v`

## 5. Closeout

- [x] 5.1 Run `python -m pytest tests/travel_engine/ tests/ -v` (or full `tests/`) — no regressions
- [x] 5.2 PowerShell purity scan under `src/travel_engine` for `src.geo|httpx|litellm|qdrant|sqlalchemy` — zero matches in real modules (stubs may still be placeholders)
- [x] 5.3 Update `docs/context.md`: Progress 4.3–4.4 ✅, Implemented modules for place_selector + day_allocator, Stubs list trimmed, Next step → 4.5; do not mark full P4 done
