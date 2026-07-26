## ADDED Requirements

### Requirement: P2 prompts define an executable verification closeout
`docs/steps/step2.md` SHALL define Steps 2.9 and 2.10 in terms that can be implemented and validated against the current P2 APIs. Step 2.9 MUST distinguish sequential idempotency from concurrent upsert safety, require separate committed sessions for the race proof, keep public network calls out of pytest, identify a session-injected seed seam for database tests, and pin readiness unit fixtures including the regression that `place_count=50` is sparse. Step 2.10 MUST include OSRM, define exact idempotency and geography-radius assertions with `limit >= place_count`, use full `/api/v1/...` paths, split Overpass/seed volume (`>= 50`) from readiness limited-band floors (`place_count >= 100` preferred), and use fail-fast smoke output. Context maintenance instructions MUST update only facts not already recorded after P2.7b/P2.8.

#### Scenario: Agent begins Step 2.9
- **WHEN** an agent reads the canonical Step 2.9 prompt
- **THEN** the requested test set includes deterministic geo fallbacks, readiness and HTTP contracts, PostGIS radius units, seed failure boundaries, same-session counter preservation, a true separate-session concurrent destination upsert, and an explicit sparse assertion for unenriched `place_count=50`

#### Scenario: Agent begins Step 2.10
- **WHEN** an agent reads the canonical Step 2.10 prompt
- **THEN** the smoke sections include Nominatim cache behavior, Overpass volume `>= 50`, seed persistence/idempotency, full public P2 HTTP routes, formula-true readiness floors, path-specific rate-limit headers, OSRM-or-fallback routing, and an explicit geography-radius invariant with sufficient `limit`

#### Scenario: Agent completes P2 verification
- **WHEN** focused P2 tests, the full suite, and the smoke script pass
- **THEN** the prompt directs the agent to mark P2.9/P2.10 complete, retain known limitations, and set P3.1 next without re-adding existing module or endpoint rows

### Requirement: P2 completion commands are usable on Windows
The P2 completion checklist SHALL identify commands that require a separate long-running server terminal and SHALL use PowerShell-compatible executable names and syntax where platform aliases differ. The checklist MUST NOT present a blocking Uvicorn command followed by HTTP commands as if the entire block runs sequentially in one terminal.

#### Scenario: Developer follows the PowerShell checklist
- **WHEN** a Windows developer reaches the server and HTTP verification sections
- **THEN** the document tells them to keep Uvicorn in a separate terminal and uses `curl.exe` or an equivalent PowerShell-safe command for curl flags
