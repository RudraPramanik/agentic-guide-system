## Purpose

Pure, confidence-based candidate normalization and dedup for travel-engine inputs so near-duplicate places collapse before scoring without merging distinct adjacent attractions.

## Requirements

### Requirement: Candidate normalizer is pure and deterministic
The project SHALL provide `src/travel_engine/candidate_normalizer.py` that normalizes and deduplicates a list of place candidates without I/O. The module MUST NOT import `src.geo`, SQLAlchemy, httpx, LLM clients, Redis, Qdrant, or call `get_settings()`. The same input list MUST produce the same survivor set and survivor ids on every run. Normalizing an already-normalized list MUST be a no-op on the survivor set (`normalize(normalize(x))` equals `normalize(x)` on place ids).

#### Scenario: Idempotent survivor set
- **WHEN** a candidate list is normalized twice
- **THEN** the set of surviving place ids is identical after the first and second pass

#### Scenario: No I/O imports
- **WHEN** the normalizer module is imported and scanned
- **THEN** it has no geo, HTTP, DB, LLM, or settings imports

### Requirement: Normalization covers name, category, and coordinates
Normalization MUST lowercase and strip punctuation/whitespace variants from names for comparison keys, map categories onto the existing structural vocabulary when a known synonym exists (unknown categories stay as-is), and round or snap coordinates only for proximity comparison without mutating published lat/lng on the survivor beyond what the module documents. Comparison keys MUST NOT replace the survivor's display name.

#### Scenario: Name variants share a comparison key
- **WHEN** two candidates differ only by case, punctuation, or surrounding whitespace in the name
- **THEN** they share the same normalized name key used for dedup

### Requirement: Dedup uses exact-ID, name, proximity, alias, and parent/child rules with confidence
Dedup MUST collapse candidates that match on any of: exact place id; same normalized name within a configured proximity; configured alias pairs; or a child place whose parent is already present when confidence clears the configured threshold. Collapse MUST keep one survivor. Confidence MUST be deterministic and documented in `travel_rules` constants. Adjacent distinct attractions that fail those rules MUST both survive. **No aggressive merging** of different names that are merely nearby.

#### Scenario: Monastery name variants collapse
- **WHEN** two monastery candidates share a normalized name (or configured alias) and lie within the configured proximity
- **THEN** exactly one survivor remains

#### Scenario: Adjacent distinct attractions stay
- **WHEN** two candidates have different normalized names, no alias link, different ids, and are not in a parent/child relation
- **THEN** both remain even if they are within the proximity radius

#### Scenario: Exact id collapse
- **WHEN** two candidates share the same place id
- **THEN** exactly one survivor remains

### Requirement: User-selected places are retained
A candidate marked user-selected MUST survive dedup even when it would otherwise lose to a higher-confidence duplicate. If two user-selected candidates collide, both MUST remain unless they share an exact place id.

#### Scenario: User-selected wins retention
- **WHEN** a user-selected candidate collides with a non-selected near-duplicate
- **THEN** the user-selected candidate is among the survivors

### Requirement: Normalizer exposes stable outputs for selectors
The normalizer MUST return the survivor candidates in a stable order (deterministic tie-break) and MAY attach a compact per-collapse reason list for tool_trace. It MUST NOT invent place ids or coordinates. Missing optional fields (aliases, parent, evidence) MUST be treated as absent, never fabricated.

#### Scenario: Missing optional fields do not invent data
- **WHEN** candidates lack aliases, parent ids, and evidence
- **THEN** normalization still completes and does not invent those fields on survivors
