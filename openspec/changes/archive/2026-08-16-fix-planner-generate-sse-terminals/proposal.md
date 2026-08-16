## Why

Guest generate on a ready destination streams SSE progress then dies with `generation_timeout` (observed in sibling FE `docs/issues/issue.md` for destination `458854b1-…`). Separately, live `PlannerService.generate` does not emit success/clarification terminals (`itinerary_done` / `clarification_needed`) after the graph finishes — only the cache-replay path and timeout/recursion `error` path emit terminals — so a successful graph can close the stream with no `trip_id` and no trip save. Frontend already parses terminals correctly; without a reliable API happy path, FE cannot open `/trips/{trip_id}`. Fix generate reliability now; defer Layla-style guidebook/PDF.

## What Changes

- Emit **locked terminal SSE events** from the live generate path after graph completion:
  - `itinerary_done` when `plan_complete` and schedule/itinerary is usable (router already saves + adds `trip_id`)
  - `clarification_needed` when `needs_clarification` (no trip save)
  - `error` remains for timeout / recursion / hard abort with no usable plan
- Emit progress hooks that the FE contract already expects when cheap to do so: at least `preferences_done` after parse and `phase_changed` on phase transitions (today mostly missing on the live path).
- Make cold generate **finish inside** `PLANNER_GENERATION_TIMEOUT_SECONDS` or fail with clear diagnostics — investigate tool-loop/LLM latency (do not “fix” by only raising the FE abort; optional modest settings tuning only if justified by measurements).
- Add/extend automated coverage: live or fake generate MUST yield exactly one terminal; success path MUST produce `itinerary_done` + `trip_id` when schedule is usable.
- Update `docs/FE_guide.md` only if wire payloads change; keep envelope rules intact.
- **Non-goals:** Layla/PDF/guidebook UI, multi-city, hotel inventory, narrative persistence on `TripOut`, evaluation HTTP, FE day-edit (F6) beyond verifying navigate-on-`trip_id`.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `planner-sse-generate`: Require live (non-cache) generate streams to close with exactly one terminal (`itinerary_done` | `clarification_needed` | `error`); clarify success/clarification payload minimums; require cold-path progress events the FE already expects.
- `planner-service-sse-bridge`: Require `PlannerService.generate` to emit those terminals (and bookend progress) from final/`TravelState` after the graph returns — not only `error` on timeout/recursion and not only cache replay.

## Impact

- **Backend (`guideagent`):** `src/planner/service.py`, graph nodes that can call `emit` (`parse_preferences`, `write_narrative`, tool executor / phase transitions), possibly small router hardening if task ends with no terminal; tests under `tests/planner/`; smoke scripts; `docs/context.md` after validate.
- **Frontend (`guideagent-frontend`, sibling):** Companion change — verify happy path after API fix; optional clearer `generation_timeout` copy. SSE client (`lib/sse/planner.ts`) already correct for terminals. Two PRs (BE then FE verify).
- **Ops:** Local Docker API + seeded destination; LLM env on API only.
- **AGENT.md:** LLM only via `core/llm/client.py`; SSE still wrapped in `wait_for` with `PLANNER_GENERATION_TIMEOUT_SECONDS`; no invented endpoints.
