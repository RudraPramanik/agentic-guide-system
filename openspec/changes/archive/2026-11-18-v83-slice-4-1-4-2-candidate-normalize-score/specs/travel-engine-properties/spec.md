## ADDED Requirements

### Requirement: Injected-off scoring matches the legacy path
With the V2 mode parameter off, `select_places` scoring MUST match the v6.1 sum-of-matching-weights path for the same candidates and interests. The setting `TRAVEL_ENGINE_V2_ENABLED` MAY exist on `Settings` for planner tools; travel-engine source MUST still not contain that name or call `get_settings()`.

#### Scenario: Injected off matches legacy scoring
- **WHEN** the same candidates and interests are scored with V2 mode injected as false
- **THEN** the selected scores match the legacy sum-of-matching-weights path

### Requirement: Idempotent dedup runs on the normalizer
Once the candidate normalizer module exists, idempotent dedup MUST assert `normalize(normalize(x))` equals `normalize(x)` on surviving place ids. The suite MUST call the normalizer. It MUST NOT skip solely because Slice 2 left the test skipped.

#### Scenario: Dedup survivor set is idempotent
- **WHEN** a fixture candidate list is normalized twice
- **THEN** the surviving place-id set is unchanged

## MODIFIED Requirements

### Requirement: Flag equivalence is the single current engine
Travel-engine source MUST NOT call `get_settings()` and MUST NOT contain the setting name `TRAVEL_ENGINE_V2_ENABLED`. V2 behavior MUST be selected only via an injected pure parameter from the planner tool boundary. With that parameter off, `select_places` (and scoring) MUST match the v6.1 sum-of-matching-weights path for the same inputs. The setting itself MAY exist on `Settings` for tools to read. The current allocator and validator remain the only implementations of those stages until later Slice 4 rows.

#### Scenario: Engine does not branch on a V2 flag
- **WHEN** the travel-engine sources are scanned
- **THEN** none of them contain `TRAVEL_ENGINE_V2_ENABLED` or call `get_settings`

### Requirement: Missing types stay skipped until their slice
Idempotent dedup MUST no longer be skipped when the candidate normalizer module exists; the suite MUST run the idempotent assertion against that module (see the added idempotent-dedup requirement). Area respect MUST continue to use the location-intelligence containment helper and MUST NOT require the engine package to import `SearchArea`. A remaining skip MUST still leave the suite exit code at 0 and MUST name the owning slice.

#### Scenario: Dedup waits for the normalizer
- **WHEN** the property suite runs and the candidate normalizer module exists
- **THEN** idempotent dedup is not skipped for “slice 4.1” and asserts the survivor-id set is unchanged on a second normalize pass

#### Scenario: Area respect waits for search area
- **WHEN** the property suite checks search-area containment
- **THEN** containment is asserted via the location-intelligence helper and the engine package does not import `SearchArea`
