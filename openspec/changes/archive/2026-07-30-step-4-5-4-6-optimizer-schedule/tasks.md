## 1. Step 4.5 — route_optimizer

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step4.md` step 4.5 (plus design D2–D4) before coding
- [x] 1.2 Implement `DroppedStop` and `OptimizeResult` in `src/travel_engine/route_optimizer.py` (Pydantic; keep `ordered: list[ScoredPlace]`)
- [x] 1.3 Implement async `optimize_route`: empty short-circuit; waypoints with `BASE_SENTINEL_ID`; matrix once per attempt; `legs_to_lookup`; brute-force permutations; consecutive `legs` on result; missing edge → `10**9`; no TSP package; no `src.geo`
- [x] 1.4 Implement drop-retry: drop lowest score (tie-break name, id); `DroppedStop(reason="exceeded_max_daily_travel")`; max `MAX_ROUTE_DROP_ATTEMPTS`; set `still_over_budget` when still over
- [x] 1.5 Run step 4.5 ✅ validation snippet from `docs/steps/step4.md`
- [x] 1.6 Confirm no `src.geo` / httpx / litellm / qdrant / sqlalchemy imports in `route_optimizer.py`

## 2. Step 4.5 — optimizer tests

- [x] 2.1 Add FakeRoutingProvider helper under `tests/` (full pairwise legs; no network)
- [x] 2.2 Create `tests/travel_engine/test_route_optimizer.py`
- [x] 2.3 Cover: Fake matrix → complete ordered day + consecutive legs length; empty day → empty result
- [x] 2.4 Cover: over-budget fixture → non-empty `dropped_stops` with reason; drop attempts capped; `still_over_budget` when still over
- [x] 2.5 Cover: asymmetric Fake forces a known best order (sanity on permutation pick)
- [x] 2.6 Run `python -m pytest tests/travel_engine/test_route_optimizer.py -v`

## 3. Step 4.6 — schedule_builder

- [x] 3.1 Re-read `docs/steps/step4.md` step 4.6 and design D6–D7 before coding
- [x] 3.2 Implement `ScheduledStop` + local naive `"HH:MM"` helpers in `src/travel_engine/schedule_builder.py`
- [x] 3.3 Implement `build_day_schedule`: empty → `[]`; morning-only stable extract (max 2 early slots) before timing; lunch gap; durations via `visit_duration_min`; no timezone/UTC
- [x] 3.4 Enforce legs contract: incompatible length / missing hop after extract → `ValueError` with clear message
- [x] 3.5 Run step 4.6 ✅ validation snippet (import + callable)
- [x] 3.6 Confirm no `src.geo` / httpx / LLM / DB imports in `schedule_builder.py`

## 4. Step 4.6 — schedule tests

- [x] 4.1 Create `tests/travel_engine/test_schedule_builder.py`
- [x] 4.2 Cover: 6-stop day → all `suggested_start_time` set; first >= `08:00`
- [x] 4.3 Cover: viewpoint in morning-only path → order ≤ 2 and start ≤ `10:30`
- [x] 4.4 Cover: lunch gap when spanning `LUNCH_BREAK_START`; mismatched / too-few legs → `ValueError`
- [x] 4.5 Run `python -m pytest tests/travel_engine/test_schedule_builder.py -v`

## 5. Closeout

- [x] 5.1 Run `python -m pytest tests/travel_engine/ tests/ -v` (or full `tests/`) — no regressions
- [x] 5.2 PowerShell purity scan under `src/travel_engine` for `src.geo|httpx|litellm|qdrant|sqlalchemy` — zero matches in real modules
- [x] 5.3 Confirm `requirements.txt` has no `tsp` / `ortools` / `python-tsp`
- [x] 5.4 Update `docs/context.md`: Progress 4.5–4.6 ✅, Implemented modules for route_optimizer + schedule_builder, Stubs list trimmed, Next step → 4.7; do not mark full P4 done
