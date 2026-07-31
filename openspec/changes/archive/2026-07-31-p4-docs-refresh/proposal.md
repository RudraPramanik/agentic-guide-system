## Why

P3 and P4 are recorded complete in `docs/context.md` (next = P5.1), but the developer manual is still frozen at **Through step: P2.10** and still lists `search/`, `travel_engine/`, and planner verification as unbuilt. That breaks the locked cadence in `docs/manual/06-maintenance.md` (refresh on full phase end) and will mislead agents starting P5. Fold the deferred P3+P4 docs sync **before** implementing the planner graph.

## What Changes

- Refresh `docs/app/documentation.md` + `docs/manual/*` to **Through step: P4.10** (catch-up for both missed phase ends).
- Sync module map / wiring / layers / recipes with `context.md`: real P3 search+enrich+index, live `search_available`, CORS, full `travel_engine/*`, `OsrmRoutingProvider`, `ToolResult`/`execute_tool` envelope, `tests/travel_engine|planner`, `scripts/test_p4_smoke.py`.
- Keep stubs explicit for what `context.md` still marks stub: planner LangGraph / tool *bodies*, trips/evaluation beyond models, `auth/dependencies.py`.
- Light-touch `docs/app/p2guide.md` so “still stubs / next phase” framing no longer claims search and travel_engine are stubs or that P3.1 is the immediate next build.
- Light-touch `docs/app/system.md` / `docs/app/lld.md` only where factual drift vs post-P4 reality exists (no architecture rewrite).
- **Non-goals:** no application code; no rewrite of `step3.md`/`step4.md`/`step5.md`/`blueprint_final.md`/`AGENT.md`/`context.md` (already current after critic patch); no inventing P5 graph/tool public APIs; no traveler/product docs.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `developer-manual`: Phase-catch-up refresh — index marker through P4.10; module map / layers / wiring / recipes / maintenance log match `context.md` after P3+P4; stubs only where context still says stub.
- `p2-study-guide`: Keep P2 engineering/interview content, but correct post-P4 “still stubs” and “next phase” framing so the guide does not contradict `context.md`.

## Impact

- Docs only: `docs/app/documentation.md`, `docs/manual/01–06`, `docs/app/p2guide.md`, optionally small corrections in `docs/app/system.md` / `docs/app/lld.md`.
- No runtime APIs, migrations, or package changes.
- Agents reading the manual after this change will correctly treat P3 search + P4 travel_engine as real and P5.1 as next.
