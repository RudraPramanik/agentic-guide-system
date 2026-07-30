## Context

`docs/blueprint_final.md` (v6) is the Planner master blueprint. `docs/blueprint.md` holds a P4 pre-flight addendum with LOCKED fixes that contradict or extend v6 (especially `travel_rules`, route ordering, CORS, SSE, cache key, agent nudge). OpenSpec change `p4-travel-engine` already plans to implement against the addendum; without merging into `blueprint_final.md`, agents have two SoTs.

This change is **documentation-only**: fold the addendum into the master file and demote the addendum to a pointer.

## Goals / Non-Goals

**Goals:**

- One authoritative Planner blueprint: updated `docs/blueprint_final.md`.
- Every LOCKED item from `docs/blueprint.md` §§A–F appears in the correct design section and/or phase step.
- Version banner / “What's in this version” table records the merge (call it **v6.1** or **v7** — see D1).
- Cross-refs in `p4-travel-engine` and `docs/context.md` point at the updated master.

**Non-Goals:**

- Implementing CORS, travel_engine, LangGraph, or SSE.
- Rewriting historical P0–P3 step text for completed work (except pytest install-order table and any factual contradiction).
- Duplicating the full addendum as a second long doc.

## Decisions

### D1 — Version label: **v6.1 (P4 pre-flight merge)**

Keep continuity with “v6 Definitive” but bump subtitle to v6.1. Avoid a full v7 rename unless the user prefers — content delta is additive/corrective, not a new architecture.

**Alt:** v7 — clearer “breaking doc” signal; optional if you want agents to cache-bust harder.

### D2 — Merge strategy: edit in place, do not append a 367-line annex

Patch the living sections:

| Addendum | Target in blueprint_final |
|----------|---------------------------|
| B travel_rules | § travel_engine → travel_rules.py code block + place_selector/day_allocator notes |
| C.1–C.2 route | § route_optimizer + P4 step 4.5 |
| A.1 CORS | New subsection under P0/P1 app stack OR Environment + new bullet in early phase; also mention in P6 ship checklist |
| A.2 SameSite | Short “Deployment decisions” box near auth/P6 |
| A.3 pytest order | Package Install Order table → move pytest to 1.11 |
| D.1 ToolContext | § ToolContext + P5 step 5.6 |
| D.2 session lifecycle | § ToolContext / P5 tools notes |
| D.3–D.4 SSE | Rewrite P6 step 6.2 sketch (queue + cancel) |
| D.5 abs min places | Settings env list + step 6.2 pre-graph check |
| D.6 cache key | Step 6.4 |
| D.7 guest ownership | Steps 6.1 / 6.3 |
| D.8 explain → tool_trace | place_selector + evaluation notes |
| D.9 agent nudge | Deterministic Fallback table + step 5.9 |
| E hardening | Short “Production hardening (deferred)” section |
| F map | Optional compact “Pre-flight merge map” — or omit if “What's in this version” covers it |

### D3 — Demote `docs/blueprint.md`

Replace body with a short notice:

- Merged into `blueprint_final.md` v6.1 on \<date\>
- Do not treat this file as competing SoT
- Keep file path so old links don’t 404; optional redirect-style first paragraph only

### D4 — Canonical corrected `travel_rules` block (paste target)

Use the addendum §B Python block verbatim (structural durations + interest weights + comments). Add explicit scoring formula under place_selector. Duration lookup rule under day_allocator / schedule_builder.

### D5 — Env vars to add in Environment Variables section

- `CORS_ALLOWED_ORIGINS` (list / comma-separated — match existing settings style in repo when documenting)
- `PLANNER_ABSOLUTE_MIN_PLACES` (e.g. 10)

### D6 — P4 step list gains 4.0 CORS (optional numbering)

Either insert **4.0 CORS middleware** before 4.1, or fold CORS into a retroactive P0/P1 note + “land before P6” — prefer **explicit 4.0** so Cursor prompts match `p4-travel-engine` tasks.

### D7 — Align `p4-travel-engine` OpenSpec text

After merge, edit that change’s proposal Impact / Conflicts to say blueprint_final v6.1 is SoT (addendum merged). No need to regenerate all P4 specs.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large markdown edit introduces accidental deletions | Edit section-by-section; diff review; keep addendum content until merge verified |
| Agents still open old `blueprint.md` | Pointer banner at top of blueprint.md |
| Over-copying addendum prose bloats master | Prefer code blocks + short LOCKED bullets in steps; drop redundant essay prose |
| Version confusion (v6 vs v6.1) | Clear banner + “What's in this version” row for pre-flight merge |

## Migration Plan

1. Patch `blueprint_final.md` sections per D2.
2. Replace `blueprint.md` with pointer.
3. One-line SoT note in `docs/context.md`.
4. Tweak `p4-travel-engine` proposal conflict note.
5. Validate: grep master for `sunrise_point`, buggy duration keys, old cache key — should be gone or only in historical “fixed” notes.

Rollback: revert the three doc files from git.

## Open Questions

1. Prefer **v6.1** vs **v7** in the title? Default: **v6.1**.
2. Keep addendum Section E (ops niceties) as a short deferred list in master? Default: **yes**, labeled non-blocking.
