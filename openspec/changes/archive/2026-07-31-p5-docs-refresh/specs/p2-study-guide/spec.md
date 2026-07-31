## ADDED Requirements

### Requirement: P2 study guide next-phase framing stays current after P5

`docs/app/p2guide.md` SHALL keep its P2 engineering/interview teaching body, but after P5 is complete in `docs/context.md` it MUST NOT claim that planner LangGraph nodes, tool bodies, orchestration, or the compiled planner graph are still stubs, and MUST NOT frame **P5.1** as the immediate next build step. Next-phase framing MUST point at **P6.1** (planner HTTP SSE / trips surface per context) consistent with `docs/context.md`. Trips CRUD HTTP and `POST /api/v1/planner/generate` MAY remain called out as not yet built.

#### Scenario: Engineer opens the guide after P5 closeout

- **WHEN** a reader opens `docs/app/p2guide.md` with context showing P5 complete
- **THEN** the guide’s “what exists / still stubs / next” lines match shipped P5 planner modules and do not tell them the LangGraph tool loop is a stub or that P5.1 is next

#### Scenario: Next phase is P6

- **WHEN** the guide states what comes after the geo foundation and later completed phases
- **THEN** it points readers to P6.1 / `docs/context.md` rather than “implement P5 now”

## MODIFIED Requirements

### Requirement: P2 study guide reflects shipped phase

`docs/app/p2guide.md` SHALL describe P2 as a completed geo-foundation phase once `docs/context.md` records P2.9/P2.10 done. It MUST NOT claim that `src/geo/*`, destinations repository/service/router/readiness, or places repository/service/router/schemas are still one-line stubs. Live destinations/places endpoints MUST be described as shipped, not “target after P2”. After later phases land, residual “still stubs” lists MUST stay consistent with `docs/context.md` (do not keep calling search, travel_engine, or P5 planner graph/tools stubs once those modules are real). Next-phase framing MUST point at the current next step in `docs/context.md` (P6.1 after P5), not a completed earlier phase.

#### Scenario: Engineer opens the guide after P2 closeout

- **WHEN** a reader opens `docs/app/p2guide.md` with context showing P2 complete
- **THEN** the guide’s phase framing and “what exists” sections match shipped P2 modules and do not tell them to treat geo/destinations/places as stubs

#### Scenario: Endpoints section is present-tense

- **WHEN** the guide lists destinations search, readiness, and places list/get
- **THEN** they are documented as live P2 endpoints consistent with `docs/context.md`, not as future targets

#### Scenario: Stub list matches context after P5

- **WHEN** a reader checks the guide’s remaining-stub callouts after P5 is complete
- **THEN** planner LangGraph / tool bodies are not listed as stubs, and next work is framed as P6.1
