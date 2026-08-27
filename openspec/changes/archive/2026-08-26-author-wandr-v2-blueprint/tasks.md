## 1. Author v2 blueprint SSOT

- [x] 1.1 Write `docs/v2_blueprint.md` in blueprint_final style (principles, resilience, failure boundaries, V0–V6 steps with ✅ proofs)
- [x] 1.2 Lock sequencing: CI → query_points → observability → harness → canonical-text → RRF → optional polish
- [x] 1.3 Document max fail-soft ladders (search, observability, cutover) and kill-switches
- [x] 1.4 Record review corrections: three tests, collection accessor, `TravelState.token_usage`, name in `_canonical_text`, `flush_tracer` already wired
- [x] 1.5 Cross-link OpenSpec siblings + `docs/next_version.md` / `docs/ci_cd_plan.md` (no duplicate package essays)

## 2. Pointers (lightweight)

- [x] 2.1 Add a short pointer at the top of `docs/next_version.md` that build steps live in `docs/v2_blueprint.md`
- [x] 2.2 Optionally note in `docs/context.md` Next-step / header that post-P7 build SSOT is `docs/v2_blueprint.md` (do not invent Progress-table P8 rows)

## 3. Verify

- [x] 3.1 Skim `docs/v2_blueprint.md` against `openspec/changes/author-wandr-v2-blueprint/design.md` Decisions D1–D6
- [x] 3.2 Confirm no product code / requirements / migrations touched by this change
- [x] 3.3 Proof: open `docs/v2_blueprint.md` — V0–V6 sections present with fallback ladders and ship proofs
