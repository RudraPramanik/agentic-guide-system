## ADDED Requirements

### Requirement: System architecture documentation is current
`docs/app/system.md` MUST serve as the architecture deep reference for the Wandr backend and MUST stay factually consistent with the current `docs/context.md` checkpoint (today: P7 complete and post-P7/v7 through at least V6.1). The document MUST describe durable architecture (purpose, layering, domain map, planner tool-loop, search, routing backends, trips/edit, observability, local Compose surface, stubs, and where to look next) rather than an early-phase step diary. It MUST NOT claim unregistered routers, missing middleware, absent Redis in Compose, or unfinished P6/P7/v7 surfaces when context marks those ✅. It MUST NOT invent stub APIs (evaluation HTTP, `auth/dependencies.py` placeholders, deferred V6.2/V6.3). It MUST NOT duplicate the full Progress table from `docs/context.md` or pin package versions (those live in `requirements.txt`). Structural rewrite of `system.md` is allowed when light-touch edits would leave material false claims.

#### Scenario: Reader gets a current architecture picture
- **WHEN** a developer or agent opens `docs/app/system.md` after this refresh with context showing P7 and V0–V6.1 done
- **THEN** they see a post-P7 / v7 architecture overview (planner SSE, trips CRUD/edit, hybrid search, routing backends, observability/evals) and do not see P0-era “no domain routers” / “no X-Request-ID yet” claims

#### Scenario: Local Compose facts match context
- **WHEN** a reader checks local infrastructure in `system.md`
- **THEN** Postgres :5433, Qdrant :6335, and Redis (Compose published host port as in context, typically :6380) are described accurately, including empty `REDIS_URL` → in-memory fallback for host/pytest vs Compose-injected Redis for the API service

#### Scenario: Stubs stay explicit
- **WHEN** a reader looks for evaluation HTTP or deferred V6.2/V6.3
- **THEN** `system.md` marks them as stub/deferred consistent with context and does not invent public APIs

#### Scenario: No Progress-table clone
- **WHEN** a reader compares `system.md` to `docs/context.md`
- **THEN** `system.md` points to context for step-level progress instead of copying the full Progress table

## MODIFIED Requirements

### Requirement: Architecture and notes docs light-touch after catch-up
`docs/app/lld.md` MUST NOT retain factual claims that contradict post-P7 / post-V6.1 `docs/context.md`. Corrections to `lld.md` remain minimal status/framing fixes — not a pattern-catalog rewrite. Stale planning notes in `docs/next_version.md` that claim `token_usage` is absent from `TravelState` MUST be corrected or clearly marked historical if still present. `docs/app/system.md` accuracy is governed by **System architecture documentation is current** (structural refresh allowed). `docs/context.md` MUST not overstate Langfuse wrapping if code has not landed lifecycle calls.

#### Scenario: context and notes match shipped observability
- **WHEN** a reader checks context / next_version notes after this change completes
- **THEN** they are not told that `token_usage` is missing from `TravelState`, and Langfuse generate lifecycle claims match the code

#### Scenario: lld status framing matches context
- **WHEN** a reader checks pattern-catalog / architecture notes in `lld.md` after the catch-up
- **THEN** those rows do not contradict P7 ✅ and V2–V6.1 ✅ in context; evaluation HTTP may still be noted as stub

#### Scenario: system.md follows the current-architecture rule
- **WHEN** a reader checks `docs/app/system.md` after this change
- **THEN** it satisfies **System architecture documentation is current** rather than being limited to light-touch row edits

### Requirement: Architecture docs light-touch after P5
After P5 closure, `docs/app/system.md` and `docs/app/lld.md` MUST NOT retain factual claims that contradict post-P5 `docs/context.md` (e.g. “planner LangGraph / tool bodies still in P5”, pattern catalog cells still implying phase-gated tool loop is unbuilt). Phase-era closure MAY use minimal status/framing fixes. Ongoing `system.md` maintenance after later phases is governed by **System architecture documentation is current**. Residual stubs at P5 closure (trips HTTP, planner HTTP) MAY remain called out as future work until context marks them real.

#### Scenario: system.md planner row matches reality
- **WHEN** a reader checks the `src/planner/` summary in `system.md` after P5 is complete in context
- **THEN** the row no longer claims LangGraph / tool bodies are only future P5 work; SSE HTTP may still be noted as P6 until context marks it real

#### Scenario: lld.md pattern table marks shipped P5 patterns
- **WHEN** a reader checks the pattern catalog in `lld.md` for Tool Registry / Phase-Gated Tool Loop / Bookend Nodes after P5 complete
- **THEN** those rows are framed as shipped (or present), not as upcoming P5-only work

### Requirement: Architecture docs light-touch after P6
After P6 closure, `docs/app/system.md` and `docs/app/lld.md` MUST NOT retain factual claims that contradict post-P6 `docs/context.md` (e.g. trips “HTTP CRUD later”, planner “HTTP generate P6” as future-only, Cache-Aside “planner cache later”). Phase-era closure MAY use minimal status/framing fixes. Ongoing `system.md` maintenance after later phases is governed by **System architecture documentation is current**. Residual stubs at P6 closure (P7 edit/replan, evaluation HTTP) MAY remain called out as future work until context marks them real.

#### Scenario: system.md trips and planner rows match reality
- **WHEN** a reader checks the `src/trips/` and `src/planner/` summaries in `system.md` after P6 is complete in context
- **THEN** the rows no longer claim trips HTTP or planner generate are only future work; P7 edit/replan may still be noted as next until context marks them real

#### Scenario: lld.md pattern table marks shipped P6 patterns
- **WHEN** a reader checks the pattern catalog in `lld.md` for Cache-Aside / rate-limiter backend Strategy after P6 complete
- **THEN** planner cache and Redis/InMemory selection are framed as shipped (or present), not as upcoming-only work
