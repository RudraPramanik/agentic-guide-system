## 1. Adopt v2 build contract (this change)

- [x] 1.1 Replace `docs/steps/step6.md` contents with the hardened v2 contract from `docs/steps/step6_suggestion.md` (build order 6.0→6.5, decision log, SSE/claim/cache/polyline locks)
- [x] 1.2 Add a one-line provenance note at the top of `docs/steps/step6_suggestion.md` that it was merged into `step6.md` via change `harden-p6-planner-api-v2` (keep file for history; do not delete unless user asks)
- [x] 1.3 Align `step6.md` Decision / cache-key section with design.md MVP lock: `sha256(destination_id + sha256(normalized_raw_input) + days_or_0 + round(base_lat,3) + round(base_lng,3))` (remove leftover “pick ONE” ambiguity)
- [x] 1.4 Confirm `openspec validate --change harden-p6-planner-api-v2` (or equivalent show/status) reports artifacts complete

## 2. Principle / coherence checks (docs only)

- [x] 2.1 Spot-check v2 prompt still forbids: Redis imports in routers, `StreamingResponse` in `PlannerService`, dual graph invoke paths, P7 edit routes, litellm outside `core/llm`
- [x] 2.2 Spot-check blueprint alignment: claim route, `accommodation_label`, `TripPlace.polyline`, anonymous claim after login
- [x] 2.3 Do **not** mark P6 ✅ in `docs/context.md` in this change (implementation not started; P5.14 gate may still be open)

## 3. Hand-off for later implementation applies (tracking only)

- [x] 3.1 Document in a short comment at end of `step6.md` (or leave existing Recommended OpenSpec batches) that code apply order remains: `6.0` → `6.1` → `6.2` → `6.3` → `6.4–6.5` as **separate** implementation changes after P5.14 is green
- [x] 3.2 After this change is applied/archived, sync delta specs to main via `/opsx:sync` or archive workflow when ready (do not invent parallel main-spec edits outside the change workflow)
