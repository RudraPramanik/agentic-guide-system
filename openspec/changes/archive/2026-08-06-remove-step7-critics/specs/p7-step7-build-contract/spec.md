## MODIFIED Requirements

### Requirement: Canonical P7 Cursor build contract v2.1

The project SHALL provide `docs/steps/step7.md` as the **sole** P7 implementation source of truth (Cursor build contract) under `docs/`. The file MUST be a non-empty hardened **v2.1** contract covering prompt substeps **7.0–7.6**, with a Decision/Fix Log that includes at least: TripEditEvent ownership (TripService creates; evaluation flag-only), shared polyline helper without collapsing `OptimizeResult.legs`, polyline persist via parallel `leg_polylines` (no invented DayPlan/ScheduledStop polyline fields), no silent `dropped_stops` on add/reoptimize, zero-network unchanged days, reorder preserve-order schedule + morning-slot warning downgrade, precise permutation check, `stop_not_found_on_day` 404, user-keyed edit rate limit, and concurrency last-write-wins MVP. Layering MUST match `step5.md` / `step6.md`: blueprint = product SoT; `step7.md` = build contract; OpenSpec = batched apply. The project MUST NOT keep a parallel P7 Cursor prompt or review draft at `docs/step7_critics.md` (or similarly named alternate under `docs/`) that agents could treat as a second contract.

#### Scenario: Step7 is the non-empty v2.1 SoT

- **WHEN** an agent opens `docs/steps/step7.md`
- **THEN** the file defines steps 7.0–7.6, a Decision/Fix Log with the v2.1 locks above, and is not an empty placeholder

#### Scenario: No parallel critics contract under docs

- **WHEN** the repository `docs/` tree is inspected for P7 build contracts
- **THEN** `docs/step7_critics.md` does not exist and `docs/steps/step7.md` is the only P7 Cursor build contract path
