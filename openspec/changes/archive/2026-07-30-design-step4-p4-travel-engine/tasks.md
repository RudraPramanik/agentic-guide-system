## 1. Author hardened `docs/steps/step4.md`

- [x] 1.1 Write header + SoT pointers: blueprint_final v6.1, context.md, AGENT.md; state that blueprint is architecture SoT and step4 is the Cursor build contract
- [x] 1.2 Add Prerequisites (P3 complete), Prompt conventions, and FAILURE BOUNDARY / ✅ Failure path standards (match step2/step3)
- [x] 1.3 Add P4 architecture diagram + locked build order `4.0 → 4.1 → … → 4.10` (design D11)
- [x] 1.4 Lock design decisions in-doc: vocabulary split, sum scoring, permutation TSP + matrix-once, `dropped_stops`, explain→trace strings, RoutingProvider DI, CORS + SameSite Option A note, naive wall-clock, soft budget, geo-coherence named constant, design-pattern map (D1–D13)
- [x] 1.5 Author Step **4.0** CORS — settings, middleware, validation, FAILURE BOUNDARY
- [x] 1.6 Author Steps **4.1–4.2** protocols + travel_rules — corrected constants, import purity, ✅ proofs
- [x] 1.7 Author Steps **4.3–4.4** place_selector + day_allocator — APIs, scoring formula, conflict filter, allocate caps, ✅ unit proofs
- [x] 1.8 Author Steps **4.5–4.6** route_optimizer + schedule_builder — FakeRoutingProvider, drop-retry, wall-clock/lunch/morning-only, ✅ proofs
- [x] 1.9 Author Steps **4.7–4.8** trip_validator + OsrmRoutingProvider/`execute_tool` skeleton — chain-of-checks, adapter outside engine, soft tool failures
- [x] 1.10 Author Steps **4.9–4.10** expanded pytest plan + `scripts/test_p4_smoke.py` real verification + full checklist / ship criteria (import guards, no ambiguous PASS)
- [x] 1.11 Ensure every code step has TASK body, FAILURE BOUNDARY, and runnable ✅ validation (Windows `Select-String` where grep was used in older prompts)

## 2. Align OpenSpec + process notes

- [x] 2.1 Confirm proposal/design/specs match the prompt locks (no pre-v6.1 “blueprint.md is SoT” language; no interest-only duration keys; no TSP package)
- [x] 2.2 Add a short note in step4.md (or checklist) that implementation OpenSpec applies should be **batched** (clusters of sub-steps), not one propose→archive per micro-step
- [x] 2.3 Note that older `openspec/changes/p4-travel-engine` doc/author tasks are superseded by this prompt; do not implement from stale tasks that contradict v6.1

## 3. Apply gate (this change only)

- [x] 3.1 Verify `docs/steps/step4.md` exists and is non-empty with sections 4.0–4.10 + verification checklist
- [x] 3.2 Run `openspec status --change design-step4-p4-travel-engine` and prepare archive after user review
- [x] 3.3 Do **not** mark P4 code complete in `docs/context.md` in this change — context updates land after implementation validations from the prompt
