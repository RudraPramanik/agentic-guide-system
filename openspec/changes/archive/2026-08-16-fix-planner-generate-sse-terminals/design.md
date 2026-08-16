## Context

See `proposal.md` for why. Observed FE failure: SSE progress then `error` / `generation_timeout` (sibling `guideagent-frontend/docs/issues/issue.md`). Code review: live `PlannerService.generate` emits `error` on timeout/recursion and tool nodes emit `tool_done` / `tool_batch_done`, but **does not** emit `itinerary_done` or `clarification_needed` after a successful/clarification graph return — only `_replay_cached` emits `itinerary_done`. The router saves trips only when it buffers `itinerary_done`.

Constraints: AGENT.md (LLM via gateway only; `wait_for` ceiling; tools via registry); router stays the SSE adapter; service stays FastAPI-free; FE already uses `fetch` + ReadableStream (`lib/sse/planner.ts`).

## Goals / Non-Goals

**Goals:**

- Every cold generate closes with exactly one terminal the FE understands.
- Successful terminals drive `save_from_state` + `trip_id`.
- Reduce or diagnose `generation_timeout` so a ready destination can complete cold generate under the configured ceiling (or fail with clear codes).
- Tests cover cold-path terminals without relying solely on mocked `on_event` that pretends success.

**Non-Goals:**

- Layla/PDF/guidebook, multi-city, narrative persistence on `TripOut`.
- Raising FE `AbortSignal` as a “fix”.
- Rewriting the travel_engine or inventing new HTTP routes.
- Shipping FE F6 Playwright proofs in this BE change (FE companion verifies navigate-on-`trip_id` after API is green).

## Decisions

### 1. Emit terminals in `PlannerService.generate` after graph return (not only in the router)

**Choice:** After `ainvoke` / timeout / recursion builds `final`, call a small pure helper (e.g. `_emit_terminal_from_state(final, on_event, already_emitted_error=…)`) that applies locked precedence and invokes `on_event`.

**Why:** Router already buffers terminals; fixing the producer keeps cache and cold paths consistent and keeps FastAPI out of the service.

**Alternatives considered:**

- Router invents `itinerary_done` from `task.result()` if queue has no terminal → rejected (duplicates business rules; harder to test without HTTP).
- Only emit from `write_narrative` / `finish_plan` nodes → incomplete for clarification END and timeout paths; service post-hook is the single choke point.

### 2. Progress emits: preferences in parse bookend; phase_changed on transition

**Choice:** `parse_preferences` emits `preferences_done` via configurable `emit` when present. Phase transitions (in `maybe_transition_phase` or tool_executor after transition) emit `phase_changed`. Optional `tool_started` can wait if cost is high — FE already ignores missing names.

**Why:** Matches `docs/FE_guide.md` without inventing new event types.

### 3. Timeout reliability: measure first, then smallest fix

**Choice:** With Docker up, one instrumented generate against the known destination: log phase, last tool, LLM call count, wall time vs `PLANNER_GENERATION_TIMEOUT_SECONDS` (45) and `LLM_TIMEOUT_SECONDS` (20). Then apply the smallest change that fits measurements, in order of preference:

1. Reduce wasted tool loops / stuck thrash (already have stuck detector — verify it fires).
2. Avoid redundant LLM work on the hot path if safe.
3. Modest settings bump only if cold path is just over budget with healthy LLM (document the new default).

**Why:** Blind timeout increases burn tokens and mask slowness; FE issue log already forbids lengthening browser abort as the fix.

### 4. Router safety net

**Choice:** If the background task completes and `pending_terminal` is still `None`, yield one `error` (`missing_terminal` or similar) so the stream never ends on progress-only frames.

**Why:** Defense in depth for future emit regressions; FE always gets a terminal.

### 5. Cross-repo delivery

**Choice:** This OpenSpec is BE-only (`guideagent`). Sibling FE gets a companion change: re-run guest generate, confirm `itinerary_done` + navigate, optionally clarify timeout copy; update `docs/issues/issue.md` status.

**Why:** Parent workspace rules: two PRs for cross-boundary work.

## Risks / Trade-offs

- [Double terminal] → Mitigation: precedence skips second emit when timeout/recursion already emitted `error`; tests assert exactly one terminal name.
- [itinerary_done without savable schedule] → Mitigation: only emit success when `save_from_state` would accept; else `error` / abort code.
- [Timeout still fails after emit fix] → Mitigation: separate latency task; emit fix alone unblocks the success path once the graph finishes under budget.
- [FE confusion destination_id vs trip_id] → Already documented in FE issue log; companion FE verify uses `trip_id` from terminal only.

## Migration Plan

1. Implement + unit/integration tests in `guideagent`.
2. Live smoke: `POST /api/v1/planner/generate` for a ready destination → exactly one terminal; success includes `trip_id`.
3. FE companion: same browser session open `/trips/{trip_id}`.
4. Update FE `docs/issues/issue.md` to resolved/partial.
5. Rollback: revert emit helper; cache path unchanged.

## Open Questions

- Whether a modest increase to `PLANNER_GENERATION_TIMEOUT_SECONDS` is justified after measurement (decide during apply, document in context.md if changed).
