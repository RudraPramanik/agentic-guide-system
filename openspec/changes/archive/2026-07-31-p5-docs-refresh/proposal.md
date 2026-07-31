## Why

P5 graph/tools work (5.1–5.11, and nearly 5.12–5.14) is in the tree, but the developer manual is still frozen at **Through step: P4.10** and still describes the planner LangGraph loop / tool bodies as stubs. That breaks the locked cadence in `docs/manual/06-maintenance.md` (refresh on phase end or every 4–5 steps) and will mislead agents starting P6. Architecture pages (`system.md`, `lld.md`) and `p2guide.md` still carry post-P4 “next = P5 / planner not built” framing that contradicts reality once P5 is recorded complete in `docs/context.md`.

## What Changes

- Refresh `docs/app/documentation.md` + `docs/manual/*` to **Through step: P5.14** (or the highest validated P5 step in `context.md` at apply time — expected P5.14 after sibling smoke/context closeout).
- Sync module map / layers / wiring / recipes with `context.md`: phase-gated tools + orchestration, `TravelState`, graph nodes (parse/agent/executor/narrative/eval), compiled graph, `PlannerService` SSE bridge, evaluation repo/service, `tests/planner/test_tool_loop.py`, `scripts/test_agent.py`.
- Keep stubs explicit for what `context.md` still marks stub after P5: trips CRUD HTTP, planner HTTP `/planner/generate` (P6), `auth/dependencies.py`, clarification-path evaluation only where still deferred.
- Light-touch `docs/app/p2guide.md` so “still stubs / next phase” framing no longer claims planner LangGraph/tool bodies are stubs or that P5.1 is the immediate next build.
- Light-touch `docs/app/system.md` / `docs/app/lld.md` only where factual drift vs post-P5 reality exists (no architecture rewrite).
- Ensure `docs/context.md` is current for the Through-step target before or as part of apply (Progress / Implemented / Stubs / Next → P6.1) — docs-only; no inventing unvalidated modules.
- **Non-goals:** no application code; no rewrite of `step5.md` / `blueprint_final.md` / `AGENT.md`; no inventing P6 HTTP generate APIs; no traveler/product docs; no full essay rewrite of system/lld.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `developer-manual`: Phase-catch-up refresh — index marker through P5 (expected P5.14); module map / layers / wiring / recipes / maintenance log match `context.md` after P5; stubs only where context still says stub (trips HTTP, planner HTTP, etc.).
- `p2-study-guide`: Keep P2 engineering/interview content, but correct post-P5 “still stubs” and “next phase” framing so the guide does not contradict `context.md`.

## Impact

- Docs only: `docs/context.md` (truth sync if still lagging), `docs/app/documentation.md`, `docs/manual/01–06`, `docs/app/p2guide.md`, opportunistic corrections in `docs/app/system.md` / `docs/app/lld.md`.
- No runtime APIs, migrations, or package changes.
- Agents reading the manual after this change will correctly treat P5 planner graph/tools/service bridge as real and P6.1 as next (once context says so).
