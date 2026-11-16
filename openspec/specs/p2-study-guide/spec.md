## Purpose

Keep `docs/app/p2guide.md` aligned with the completed P2 geo-foundation phase: shipped modules, live endpoints, and formula-true readiness floors for engineers and interview prep.

## Requirements

### Requirement: P2 study guide reflects shipped phase

`docs/app/p2guide.md` SHALL describe P2 as a completed geo-foundation phase once `docs/context.md` records P2.9/P2.10 done. It MUST NOT claim that `src/geo/*`, destinations repository/service/router/readiness, or places repository/service/router/schemas are still one-line stubs. Live destinations/places endpoints MUST be described as shipped, not “target after P2”. After later phases land, residual “still stubs” lists MUST stay consistent with `docs/context.md` (do not keep calling search, travel_engine, or P5 planner graph/tools stubs once those modules are real). The guide SHALL keep its P2 engineering and interview teaching body. Its header and next-step lines MUST point at `docs/context.md` for what to do next and MUST NOT name a finished phase, including P3.1, P5.1, P5.12, or P6.1, as the current build step when `docs/context.md` records that phase complete.

#### Scenario: Engineer opens the guide after P2 closeout

- **WHEN** a reader opens `docs/app/p2guide.md` with context showing P2 complete
- **THEN** the guide’s phase framing and “what exists” sections match shipped P2 modules and do not tell them to treat geo/destinations/places as stubs

#### Scenario: Endpoints section is present-tense

- **WHEN** the guide lists destinations search, readiness, and places list/get
- **THEN** they are documented as live P2 endpoints consistent with `docs/context.md`, not as future targets

#### Scenario: Stub list matches context after P4

- **WHEN** a reader checks the guide’s remaining-stub callouts after P4 is complete
- **THEN** search and travel_engine are not listed as stubs, and next work is not framed as P3.1

#### Scenario: Stub list matches context after P5

- **WHEN** a reader checks the guide’s remaining-stub callouts after P5 is complete
- **THEN** planner LangGraph / tool bodies are not listed as stubs, and next work is not framed as P5.1

#### Scenario: Stub list matches context after later phases

- **WHEN** a reader checks the guide’s remaining-stub callouts after P7 and v7 V0–V6.1 are complete in `docs/context.md`
- **THEN** search, travel_engine, and the planner tool loop are not listed as stubs, and the header points at `docs/context.md` instead of naming P5.12 or another finished step as next

#### Scenario: Header does not revive a finished phase

- **WHEN** a reader reads only the header of `docs/app/p2guide.md`
- **THEN** they are not told that the next build step is P5.12, P5.1, or P6.1

### Requirement: P2 study guide keeps formula-true readiness floors

The study guide’s readiness acceptance language MUST distinguish seed/Overpass volume (`place_count >= 50`) from unenriched limited-band scoring. Limited-band / `score >= 0.35` claims MUST require `place_count >= 88` at minimum and SHOULD cite `place_count >= 100` for exact score `0.4`. The guide MUST NOT teach that `place_count >= 50` alone implies `tier=limited`.

#### Scenario: Interview Q on limited after seed

- **WHEN** a reader uses the guide’s readiness section or Q&A about post-seed limited tier
- **THEN** the answer is consistent with `compute_readiness(50,0,0,False)` being sparse (`score=0.2`) and limited-band needing a higher place_count floor
