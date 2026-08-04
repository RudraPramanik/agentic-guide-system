## Context

P5 tool-loop + `PlannerService` are real; NIM smoke runs the agent to WRAP_UP but section 4 fails because Darjeeling days often violate `trip_validator` after packing. Deterministic probes (search→rank→route→schedule→validate) reproduce the same classes of errors without the LLM: travel slightly/severely over `MAX_DAILY_TRAVEL_MIN`, morning-only viewpoints in slot 3 or after `10:30`, geo coherence stddev > 15km. Nominatim is unrelated (User-Agent only; smoke uses seeded DB). Softening smoke or relaxing validator thresholds would stamp P5 without fixing the product. Constraints: `travel_engine` stays pure; routing via `RoutingProvider` only; constants in `travel_rules.py`.

## Goals / Non-Goals

**Goals:**

- Make packing + optimize + schedule produce days that are *much more likely* to pass the existing validator without changing validator thresholds.
- Cap morning-only stops at ≤2 per day at allocate time.
- Soft geo (option A): prefer coherent clusters / better spill targets; still allow spill when capacity forces it.
- Optimizer returns full pairwise `legs`; drops until under travel budget or one stop left.
- Schedule morning extract does not park excess morning-only into invalid mid-day slots.
- Unit tests lock the regression modes; enable a later green `scripts/test_agent.py` without softening §4.

**Non-Goals:**

- Raising `GEO_COHERENCE_MAX_STDDEV_KM`, `MAX_DAILY_TRAVEL_MIN`, or morning latest start.
- Softening smoke section 4 / accepting abort as PASS.
- Hard geo reject on projected stddev (option B) — deferred if soft packing still fails Darjeeling.
- Nominatim/OSRM credentials, LLM gateway, P6 HTTP.
- Guaranteeing every seed dataset always validates (hill-town data may still need replan tools); goal is remove systematic packing bugs.

## Decisions

1. **Morning-only cap in `allocate_days` (source of truth)**  
   When adding a place whose `category ∈ MORNING_ONLY_CATEGORIES`, refuse if the target day already has 2 such places; try another day or omit.  
   *Alternatives:* only fix in schedule (drops info; validator still sees bad days if schedule omits inconsistently) — rejected as primary. Schedule remains a safety net.

2. **Soft geo packing (option A)**  
   Keep `CLUSTER_RADIUS_KM` clustering. When spilling, prefer the underfilled day whose current centroid is closest (haversine) to the candidate, not only fewest places. Do **not** compute validator stddev and hard-block.  
   *Alternatives:* hard reject if projected stddev > 15km (B) — deferred todo if A insufficient.

3. **Optimizer `legs` = full `travel_matrix` result**  
   Consecutive chain alone breaks morning reorder (`ValueError` / `tool_error`). Full directed pairwise matches schedule “lookup-complete” path and existing schedule tests.  
   *Alternatives:* disable morning reorder when legs incomplete — weakens morning product rule.

4. **Drop until under budget or one stop**  
   Loop while `total > MAX_DAILY_TRAVEL_MIN` and `len(remaining) > 1`, each attempt calling `travel_matrix`. Set `MAX_ROUTE_DROP_ATTEMPTS = MAX_PLACES_PER_DAY - 1` (5) so a full day can thin to one stop. `still_over_budget` only when a single remaining stop still exceeds the cap.  
   *Alternatives:* keep literal blueprint “max 3” — rejected; leaves multi-stop days knowingly over budget (Darjeeling day2 ~337min with 3 stops). Document divergence from blueprint “max 3” in this design.

5. **Schedule excess morning**  
   `_extract_morning_first`: place `k=min(2,n)` morning stops first, then **non-morning**, omit remaining morning-only from the timed schedule (they are packing bugs if present; allocator should have prevented). Document omission.  
   *Alternatives:* append excess morning at end — still fails `check_morning_slots`.

6. **Smoke / context ownership**  
   This change ships packing + tests. Re-run smoke as a verification task; `docs/context.md` P5 stamp stays with completing `ship-p5-14-smoke-nvidia-nim` once §4 is green (or a one-line handoff task here that only updates context if smoke passes and that change is still open).

## Risks / Trade-offs

- [Thinner days / more omitted POIs] → Mitigation: omit only when caps force it; higher scores still preferred.
- [Soft geo still fails coherence on bad seeds] → Mitigation: deferred option B or radius filter at search; do not relax validator in this change.
- [Blueprint “max 3 drops” divergence] → Mitigation: document; constant remains named `MAX_ROUTE_DROP_ATTEMPTS` in `travel_rules.py`.
- [Single stop still over budget (base→POI > 180)] → Mitigation: `still_over_budget=True`; replan/expand must find nearer POIs — not packing’s job to invent times.
- [Existing optimizer tests expect consecutive `legs` length] → Mitigation: update tests to full pairwise size (already partially done in working tree).

## Migration Plan

1. Implement allocator morning cap + soft spill preference; unit tests.
2. Finalize optimizer full-matrix legs + drop-until-under; update `MAX_ROUTE_DROP_ATTEMPTS`; unit tests.
3. Schedule excess-morning omission; unit tests.
4. `pytest tests/travel_engine/ -q` then full `tests/`.
5. Optional live: deterministic Darjeeling tool pipeline + `scripts/test_agent.py`.
6. Rollback: revert travel_engine commits; no DB migrations.

## Open Questions

- None blocking — option A locked by product owner. Escalate to option B only if post-fix Darjeeling deterministic validate still fails geo coherence after morning/travel fixes.
