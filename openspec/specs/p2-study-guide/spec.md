## Purpose

Keep `docs/app/p2guide.md` aligned with the completed P2 geo-foundation phase: shipped modules, live endpoints, and formula-true readiness floors for engineers and interview prep.

## Requirements

### Requirement: P2 study guide reflects shipped phase

`docs/app/p2guide.md` SHALL describe P2 as a completed geo-foundation phase once `docs/context.md` records P2.9/P2.10 done. It MUST NOT claim that `src/geo/*`, destinations repository/service/router/readiness, or places repository/service/router/schemas are still one-line stubs. Live destinations/places endpoints MUST be described as shipped, not “target after P2”. Next-phase framing MUST point at P3 (enrich + Qdrant), not “implement P2 now”.

#### Scenario: Engineer opens the guide after P2 closeout

- **WHEN** a reader opens `docs/app/p2guide.md` with context showing P2 complete
- **THEN** the guide’s phase framing and “what exists” sections match shipped modules and do not tell them to treat geo/destinations/places as stubs

#### Scenario: Endpoints section is present-tense

- **WHEN** the guide lists destinations search, readiness, and places list/get
- **THEN** they are documented as live P2 endpoints consistent with `docs/context.md`, not as future targets

### Requirement: P2 study guide keeps formula-true readiness floors

The study guide’s readiness acceptance language MUST distinguish seed/Overpass volume (`place_count >= 50`) from unenriched limited-band scoring. Limited-band / `score >= 0.35` claims MUST require `place_count >= 88` at minimum and SHOULD cite `place_count >= 100` for exact score `0.4`. The guide MUST NOT teach that `place_count >= 50` alone implies `tier=limited`.

#### Scenario: Interview Q on limited after seed

- **WHEN** a reader uses the guide’s readiness section or Q&A about post-seed limited tier
- **THEN** the answer is consistent with `compute_readiness(50,0,0,False)` being sparse (`score=0.2`) and limited-band needing a higher place_count floor
