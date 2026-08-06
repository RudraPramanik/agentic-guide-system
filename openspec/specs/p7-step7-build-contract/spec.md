## Purpose

Canonical P7 Cursor build contract (`docs/steps/step7.md` v2.1) — planning SoT for Edit & Replan implementation batches.

## Requirements

### Requirement: Canonical P7 Cursor build contract v2.1

The project SHALL provide `docs/steps/step7.md` as the single P7 implementation source of truth (Cursor build contract). The file MUST be a non-empty hardened **v2.1** contract covering prompt substeps **7.0–7.6**, with a Decision/Fix Log that includes at least: TripEditEvent ownership (TripService creates; evaluation flag-only), shared polyline helper without collapsing `OptimizeResult.legs`, polyline persist via parallel `leg_polylines` (no invented DayPlan/ScheduledStop polyline fields), no silent `dropped_stops` on add/reoptimize, zero-network unchanged days, reorder preserve-order schedule + morning-slot warning downgrade, precise permutation check, `stop_not_found_on_day` 404, user-keyed edit rate limit, and concurrency last-write-wins MVP. Layering MUST match `step5.md` / `step6.md`: blueprint = product SoT; `step7.md` = build contract; OpenSpec = batched apply. `docs/step7_critics.md` MUST NOT be treated as the build contract.

#### Scenario: Step7 is the non-empty v2.1 SoT

- **WHEN** an agent opens `docs/steps/step7.md` after this change is applied
- **THEN** the file defines steps 7.0–7.6, a Decision/Fix Log with the v2.1 locks above, and is not an empty placeholder

#### Scenario: Critics file is not the SoT

- **WHEN** an implementer chooses between `docs/steps/step7.md` and `docs/step7_critics.md`
- **THEN** `docs/steps/step7.md` is authoritative for implementation behavior
