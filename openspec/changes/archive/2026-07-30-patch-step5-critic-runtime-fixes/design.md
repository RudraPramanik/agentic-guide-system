## Context

P4 is complete (`docs/context.md`). Next is P5 from `docs/steps/step5.md`, whose product locks come from `docs/blueprint_final.md` v6.1. The critic addendum (`docs/steps/step5_critic.md`) does **not** invent a new architecture — it tightens execution semantics that the draft prompt and blueprint leave ambiguous: how `ToolContext` is threaded into a **cached singleton** compiled graph, who may call `execute_tool`, how list fields merge, and what state exists after `asyncio.wait_for` cancellation.

Engineering judgment vs blueprint:

| Critic fix | Verdict | Why |
|---|---|---|
| 1 Config-only ToolContext | **Accept** | Blueprint still says “closure / configurable”; with compile-once (5.11) a closure is a real cross-request leak |
| 2 Single executor pathway | **Accept** | Matches AGENT.md “all tool execution via execute_tool”; removes dual bookkeeping paths in 5.9/5.11 |
| 3 Explicit list append | **Accept** | LangGraph last-write-wins would silently truncate `tool_trace` / evaluation |
| 4 `last_known_state` on timeout | **Accept** | Cancelled task cannot return accumulated state; conflicts with “evaluation always runs” |
| 5 Tools read-only; `apply_tool_result` sole writer | **Accept** | Stronger than blueprint’s `ToolContext.state` read/write helpers — better auditability |
| 6 Stuck-detector unconditional | **Accept** | Documents why `unknown_tool` skipping `tool_loop_count` is safe |
| 7 Exact `langgraph` pin + hello-world | **Accept** | Matches project exact-pin convention |
| 8 REPLAN coarse-graining rationale | **Accept** | Docs-only; intentional asymmetry, not a violation |
| Minor named constants + itinerary map | **Accept** | Aligns with P4 “no magic numbers” |

## Goals / Non-Goals

**Goals:**
- Fold all accepted critic fixes into `docs/steps/step5.md` at the listed sub-steps before any 5.9+ code lands.
- Align conflicting SoT sentences in `blueprint_final.md` and add the config-only rule to `AGENT.md`.
- Encode regression scenarios in step 5.13 so implementers cannot “pass” with last-write-wins or closure DI.

**Non-Goals:**
- Implementing LangGraph nodes, tools, or SSE HTTP (P6).
- Changing travel_engine algorithms or PHASE_TOOLS membership.
- Archiving the prior `design-step5-p5-tool-loop-agent` change (already complete; this is a follow-on patch).

## Decisions

### D1 — Patch step5.md in place; keep critic as companion
**Choice:** Edit `docs/steps/step5.md` directly; leave `step5_critic.md` as the rationale companion (or mark “applied”).  
**Alt:** Replace step5 wholesale with critic-only text → loses the good P4 forward-locks already in step5.  
**Rationale:** Critic is a patch addendum, not a replacement prompt.

### D2 — ToolContext only via `config["configurable"]["tool_context"]`
**Choice:** Forbid closures/module-globals; every node reads ctx from config each call.  
**Alt:** Closure factory per invoke rebuilding the graph → defeats 5.11 compile-once.  
**Rationale:** Cached compiled graph + per-request ctx is the only safe pairing.

### D3 — Agent never calls `execute_tool`; default path synthesizes `pending_tool_calls`
**Choice:** Unconditional edge `agent → tool_executor`; agent only decides/synthesizes calls.  
**Alt:** Agent executes default inline (current step5 draft) → dual pathways and messy edges.  
**Rationale:** One place for trace/count/stuck bookkeeping.

### D4 — Pass read-only state into `execute_tool`; mutate only in `apply_tool_result`
**Choice:** Remove mutation callbacks / writable `state` on ToolContext; signature may take a state snapshot for reads.  
**Alt:** Keep blueprint `ToolContext.state` with typed helpers → still two writers under pressure.  
**Rationale:** Pure tools + single audit point.

### D5 — Timeout capture via emit hooks updating `last_known_state` outside the task
**Choice:** Service-level dict updated whenever nodes emit checkpoints; on `TimeoutError` merge that snapshot then `record_evaluation`.  
**Alt:** Try to inspect cancelled task result → unreliable under asyncio cancellation.  
**Rationale:** Preserves evaluation-always-runs without hanging.

### D6 — Docs apply order (from critic)
Independent first: named constants + langgraph pin (5.2/5.3/5.6) → ToolContext/mutation language (5.1/5.5) → agent/executor rewrite (5.9/5.11) → service timeout (5.12) → tests (5.13).

## Risks / Trade-offs

- [Risk] Blueprint vs step5 drift if only step5 is patched → Mitigation: also update the ToolContext / agent / graph-edge sentences in `blueprint_final.md` and the P5 locks bullet in `planner-blueprint-sot`.
- [Risk] `last_known_state` is a shallow dict copy → Mitigation: document “snapshot after each tool_executor cycle”; deep-copy only if nested mutation bugs appear in tests.
- [Risk] REPLAN tools still aggregate multiple engine steps under one `tool_loop_count` tick → Mitigation: document intentional; put sub-step timings in `ToolResult.data` if needed later — do not inflate loop count.
- [Risk] Floating `langgraph>=0.2.0` already in step5 draft gets committed by an eager implementer → Mitigation: change pin text **before** any apply of 5.6; pin exact version after hello-world verify.

## Migration Plan

1. Apply this OpenSpec change (docs only): patch step5, blueprint snippets, AGENT.md rule, specs.
2. Implementers continue P5 clusters from the updated prompt (`/opsx:apply` on implementation changes).
3. Rollback: revert the three doc files; no runtime migration.

## Open Questions

- Exact `langgraph==0.2.x` patch version: leave as “pin during 5.6 hello-world” (do not invent XX now).
- Whether `execute_tool` signature gains an explicit `state` read-arg vs a frozen snapshot on ctx: prefer explicit arg in step5 rewrite to avoid accidental mutation (match critic Fix 2 sample).
