## ADDED Requirements

### Requirement: Step 7.4 verification gate for edit/replan behavior

The P7 day-edit behavior contract in this capability MUST be proven by `tests/trips/test_edit_replan.py` (step **7.4** in `docs/steps/step7.md`), not only by thin 7.3 HTTP smoke. That suite MUST exercise FakeRoutingProvider-backed service and thin HTTP cases covering reorder/remove/add/reoptimize success and failure paths, ownership 403, rate-limit 429, preserve-order / morning-slot asymmetry, dropped_stops rollback, single `TripEditEvent` on success, zero audit rows on validation failure, and mutated-day-only RoutingProvider calls. Claiming the HTTP + service edit surface complete without this suite green is forbidden.

#### Scenario: Behavior contract verified by edit/replan suite

- **WHEN** step 7.4 validation runs
- **THEN** `python -m pytest tests/trips/test_edit_replan.py -v` is green and covers the locked scenario matrix before advancing to 7.5
