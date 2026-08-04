## 1. Rules + optimizer foundation

- [x] 1.1 Set `MAX_ROUTE_DROP_ATTEMPTS = MAX_PLACES_PER_DAY - 1` in `src/travel_engine/travel_rules.py`; confirm validator thresholds unchanged
- [x] 1.2 Ensure `optimize_route` returns full pairwise `travel_matrix` as `legs` (not consecutive-only); update `tests/travel_engine/test_route_optimizer.py` accordingly
- [x] 1.3 Change drop-retry to continue while over `MAX_DAILY_TRAVEL_MIN` and `len(remaining) > 1` (within `MAX_ROUTE_DROP_ATTEMPTS`); `still_over_budget` only if remaining path still over cap
- [x] 1.4 Add/adjust unit tests: drop until under budget; single-stop still-over case

## 2. Day allocator packing

- [x] 2.1 Cap morning-only (`MORNING_ONLY_CATEGORIES`) at ≤2 per day in `allocate_days` (spill/omit when full)
- [x] 2.2 Soft geo spill (option A): when spilling, prefer nearer day centroid (in-module haversine) among underfilled days that can accept the place — no hard geo-coherence reject
- [x] 2.3 Unit tests: third viewpoint not packed onto a day with two; spill prefers nearer day

## 3. Schedule builder safety net

- [x] 3.1 Update `_extract_morning_first` / `build_day_schedule` so excess morning-only beyond two are omitted from the timed day (not left in slot 3+)
- [x] 3.2 Unit tests: three viewpoints → at most two morning-only in schedule orders 1–2; lookup-complete legs still required for reorder

## 4. Verification

- [x] 4.1 Run `python -m pytest tests/travel_engine/ -q` green
- [x] 4.2 Run `python -m pytest tests/ -q` green
- [x] 4.3 Optional live: deterministic Darjeeling search→rank→route→schedule→validate (note remaining errors if any; do not relax rules)
- [x] 4.4 Re-run `python scripts/test_agent.py` with existing NIM `LLM_*` env; if section 4 green, finish/resume `ship-p5-14-smoke-nvidia-nim` context stamp — do not soften smoke criteria here
