## Purpose

Property tests for the current travel engine that lock §11.6 relations, call the Slice 2.3 coherence metric, and record a failure on today's engine instead of changing that engine.

## Requirements

### Requirement: Property tests do not change the engine
The §11.6 suite MUST live under the travel-engine tests. It MUST NOT add or edit travel-engine source. It MUST NOT import a provider SDK, an HTTP client, or a database session. Where a test needs routing responses, it MUST use the existing in-test fake routing provider. `pytest tests/travel_engine -v` MUST exit 0. A property that fails on the current engine MUST be reported by name as a finding, and the test MUST be an expected failure that cites that finding. The engine source MUST stay unchanged.

#### Scenario: Suite exits zero without an engine edit
- **WHEN** the travel-engine test suite runs after this change
- **THEN** the process exits 0 and the travel-engine source diff is empty

#### Scenario: A current failure is a named finding
- **WHEN** a property does not hold for the current engine
- **THEN** the suite records that property's name as a finding and does not edit the engine

### Requirement: Determinism and order invariance
The same candidate input and the same routing responses MUST produce the same selected set and the same day assignment on two runs. Shuffling the candidate input order MUST NOT change the selected set or which day each selected place is assigned to. These tests MUST call the existing selector and allocator.

#### Scenario: Two runs match
- **WHEN** the same candidates and the same routing responses are planned twice
- **THEN** the selected set and the day assignment are identical

#### Scenario: Shuffled input keeps the selection
- **WHEN** the same candidates are passed in a different order
- **THEN** the selected set and the day assignment are unchanged

### Requirement: Removal keeps uniqueness and chronology
Removing any one stop from an itinerary that already has unique place ids and non-decreasing start times MUST leave unique place ids and non-decreasing start times. The test MUST apply that removal in the fixture. It MUST NOT add a remove API to the engine.

#### Scenario: One stop removed
- **WHEN** any single stop is removed from a valid itinerary fixture
- **THEN** no place id repeats and the remaining start times are non-decreasing

### Requirement: Coherence does not improve when a distant point is added
The monotonic-coherence property MUST call the geographic coherence metric from the metrics capability. It MUST NOT reimplement the dispersion formula. Adding a coordinate that is farther from the current centroid than every existing coordinate MUST NOT decrease that metric. A lower kilometer value is tighter, so a decrease would be an improvement and MUST fail this property.

#### Scenario: Distant point uses the shared metric
- **WHEN** a day produced by the current allocator gains a coordinate farther from its centroid than every existing point
- **THEN** the coherence metric's kilometer value does not decrease

### Requirement: Budget and schedule properties
No day returned by the current allocator MUST exceed the configured active-time cap or the configured per-day place cap. Start times within a built day MUST be strictly non-decreasing. When a scheduled leg has a matching route leg, the scheduled duration MUST equal that route leg's duration. A violation on the current engine MUST follow the finding rule and MUST NOT change the engine.

#### Scenario: Allocated days respect the caps
- **WHEN** the allocator packs a fixture that fits the configured caps
- **THEN** every returned day is within the active-time cap and the per-day place cap

#### Scenario: Schedule times do not go backwards
- **WHEN** the schedule builder emits a day
- **THEN** each start time is strictly later than the previous start time, or the property is a named finding

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
