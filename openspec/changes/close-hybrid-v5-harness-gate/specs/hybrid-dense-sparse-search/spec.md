## MODIFIED Requirements

### Requirement: Cutover is harness-gated and reversible via env
Traffic MUST NOT flip to V2 until the target destinations are indexed and the golden harness passes against V2 using a **live** (non-fixtures-only) pipeline run when the LLM key and stack are available. A fixtures-only run MUST NOT alone close the cutover checklist. Rollback MUST be possible by flipping the accessor/env and/or disabling sparse without schema migrations. Frontend and HTTP contracts MUST remain unchanged across cutover. After cutover, closing the V5 gate REQUIRES a live harness exit 0 against the active collection (or an explicit baseline update after reviewing live verdicts when the prior baseline was fixture-mode).

#### Scenario: Empty V2 is not used as live traffic
- **WHEN** V2 exists but has zero indexed points for a destination
- **THEN** operators MUST NOT flip the accessor to V2 for that traffic until index + harness validation succeed

#### Scenario: Live harness required to close cutover
- **WHEN** operators close the V5 hybrid cutover checklist with LLM key and stack available
- **THEN** they MUST run the golden harness without fixtures-only mode against the active places collection and obtain exit 0 (or update baseline only after reviewing live case verdicts)

#### Scenario: Fixtures-only does not close cutover
- **WHEN** the only successful harness run is fixtures-only (or falls back to fixtures because the LLM key is empty)
- **THEN** that run MUST NOT alone mark hybrid cutover validation complete

#### Scenario: Rollback restores dense-healthy path
- **WHEN** operators set sparse off and/or point the accessor back to the validated collection
- **THEN** search remains healthy under tests without requiring a DB migration

#### Scenario: No frontend contract change
- **WHEN** hybrid cutover completes
- **THEN** HTTP paths, DTO envelopes, and SSE event names used by the frontend remain unchanged
