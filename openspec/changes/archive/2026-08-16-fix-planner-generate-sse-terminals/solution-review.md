# Solution review — fix generate → trip result (no Layla)

**Date:** 2026-08-16  
**Status:** **Implemented and live-proved** (OpenSpec tasks 17/17) — FE browser companion verify still open in sibling repo  
**BE change:** `guideagent/openspec/changes/fix-planner-generate-sse-terminals/`  
**FE companion:** `guideagent-frontend/openspec/changes/verify-generate-trip-after-api-fix/`

---

## 1. Problem (what we are solving)

We need a reliable **search → generate → `trip_id` → trip page** loop. Layla-style guidebook/PDF is explicitly **out of scope** for now.

### What we already know

| Fact | Source |
|------|--------|
| FE streams `POST /planner/generate` correctly (`fetch` + SSE parser) | `guideagent-frontend/lib/sse/planner.ts` |
| Live repro ended with SSE `error` / **`generation_timeout`** | `guideagent-frontend/docs/issues/issue.md` |
| Destination had enough places (132); readiness `limited` (not 409) | same |
| FE correctly shows failure and does **not** auto-retry | same |
| Backend hard ceiling is **`PLANNER_GENERATION_TIMEOUT_SECONDS` = 45** | `src/config.py` |
| Live success path does **not** emit `itinerary_done` today (only cache replay + timeout `error`) | code review: `PlannerService.generate` / `cache._replay_cached` |
| Router only saves a trip when it buffers **`itinerary_done`** | `src/planner/router.py` |

So there are **two** stacked issues:

1. **Timeout** — cold graph often exceeds 45s → FE never gets a trip (observed).
2. **Missing success terminal** — even if the graph finishes under budget, cold path may close **without** `itinerary_done` / `trip_id` (code gap; would look like “no generate result”).

---

## 2. Preferred approach (sequencing)

**Yes — fix generate first; Layla later.** That remains the right product order.

```
API healthy + ready destination
    → cold POST /planner/generate
    → exactly one terminal
    → itinerary_done + trip_id  (or clear error / clarification)
    → FE opens /trips/{trip_id} in same browser session
```

Only after that loop is green do we design guidebook/PDF UX.

---

## 3. Solution (backend)

### A. Emit terminals from live generate (required)

After graph return (and after timeout/recursion final state), `PlannerService.generate` must emit **exactly one** terminal via existing `on_event`:

| Final state | Terminal |
|-------------|----------|
| Timeout / recursion already emitted | keep single `error` (no second) |
| `needs_clarification` | `clarification_needed` + question |
| `plan_complete` + usable schedule | `itinerary_done` (router adds `trip_id`) |
| Otherwise | `error` with stable code |

Also emit cold-path progress FE already expects: `preferences_done`, `phase_changed`.

Router safety net: if task ends with **no** terminal buffered → yield one `error` (never progress-only hang).

### B. Timeout reliability (measure, then smallest fix)

Do **not** “fix” by lengthening the browser abort (burns tokens after the UI gave up).

1. One instrumented generate: which phase/tool/LLM call eats the 45s.
2. Prefer fixing waste (stuck loops, redundant LLM).
3. Only then consider a **documented** modest increase to `PLANNER_GENERATION_TIMEOUT_SECONDS` if the path is healthy but just over budget.

### C. Tests / proof

- Unit: terminal precedence helper.
- Integration: cold `generate` emits `itinerary_done` without cache replay.
- SSE: `trip_id` on save; clarification/error save nothing.
- Live smoke against a ready destination.

---

## 4. Solution (frontend — sibling)

FE is **mostly correct**. Companion work:

1. After API fix: guest generate on a ready destination → assert UI navigates to `/trips/{trip_id}`.
2. Keep treating `generation_timeout` as terminal (no auto-retry).
3. Optional: clearer copy that timeout is an **API planner budget**, not a missing `NEXT_PUBLIC_*` key.
4. Update `docs/issues/issue.md` when resolved.
5. Do **not** confuse `destination_id` with `trip_id` (already documented).

Two PRs: **BE first**, then FE verify.

---

## 5. Non-goals (this round)

- Layla / PDF export / multi-city / hotel inventory  
- Persisting day narrative on `TripOut`  
- Evaluation HTTP  
- Chat shell / Vercel AI SDK as planner client  

---

## 6. Review checklist (for you)

- [ ] Agree: terminals must come from **service emit bridge**, not FE inventing a trip.
- [ ] Agree: timeout diagnosis before blindly raising FE or API timeouts.
- [ ] Agree: FE companion is verify-only unless copy needs a small tweak.
- [ ] Ready to run `/opsx:apply` (or ask to implement) on `fix-planner-generate-sse-terminals`.

---

## 7. Artifact index

| Artifact | Path |
|----------|------|
| Proposal | `openspec/changes/fix-planner-generate-sse-terminals/proposal.md` |
| Design | `openspec/changes/fix-planner-generate-sse-terminals/design.md` |
| Specs | `openspec/changes/fix-planner-generate-sse-terminals/specs/planner-sse-generate/spec.md` |
| Specs | `openspec/changes/fix-planner-generate-sse-terminals/specs/planner-service-sse-bridge/spec.md` |
| Tasks | `openspec/changes/fix-planner-generate-sse-terminals/tasks.md` |
| This review | `openspec/changes/fix-planner-generate-sse-terminals/solution-review.md` |
| FE companion | `../guideagent-frontend/openspec/changes/verify-generate-trip-after-api-fix/` |
