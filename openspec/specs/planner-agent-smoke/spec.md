## Purpose

P5.14 agent smoke script + context closeout: sectioned fail-loud `scripts/test_agent.py` and context.md update only after green gates.

## Requirements

### Requirement: scripts/test_agent.py is a sectioned P5 smoke
The project SHALL add `scripts/test_agent.py` that invokes `PlannerService.generate` directly (no HTTP router required) with `raw_input="3 days offbeat photography budget"` against a seeded+enriched+indexed Darjeeling destination. The script MUST print numbered section headers and exit non-zero on the first failure (never ambiguous PASS). Sections MUST cover:

1. Settings planner bounds present
2. Graph compiles
3. `generate()` completes
4. `errors==[]` (or only soft warnings), `abort_triggered==False`
5. `days==3`; all stops have lat/lng + `suggested_start_time`
6. `tool_trace` non-empty; print summary table
7. Evaluation row written (query DB)
8. Import guards: no litellm outside `core/llm/client.py`; no tool-impl imports under `graph/nodes`; `travel_engine` still pure
9. OPTIONAL: print Langfuse trace URL if keys configured

#### Scenario: Smoke fails loud without seed or LLM
- **WHEN** required env / seeded destination / LLM keys are missing
- **THEN** the script exits non-zero with a clear section header (does not print overall success)

#### Scenario: Green smoke proves itinerary shape
- **WHEN** smoke runs successfully against Darjeeling
- **THEN** sections 1–8 pass including day count, stop fields, tool_trace, and evaluation row

### Requirement: context.md marks P5 complete only after green gates
`docs/context.md` MUST be updated only after `scripts/test_agent.py` and `python -m pytest tests/ -v` pass. The update MUST:

- Set Next step → P6.1; Progress rows 5.1–5.14 ✅
- List implemented planner tools, graph, service bridge, evaluation service
- Keep trips CRUD / planner HTTP router as P6 stubs
- NOT claim P6 complete or register `/planner/generate` as a live endpoint

#### Scenario: HTTP generate still unregistered after P5
- **WHEN** the FastAPI app routes are inspected after this batch
- **THEN** no route path contains `planner/generate`
