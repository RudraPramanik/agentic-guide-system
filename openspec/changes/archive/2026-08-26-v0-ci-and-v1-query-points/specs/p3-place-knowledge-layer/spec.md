## ADDED Requirements

### Requirement: Semantic search uses the Qdrant query-points path
`search_places` SHALL issue destination-scoped retrieval via the Qdrant client's query-points API (not the deprecated search API). Mapping from the query response to `PlaceSearchResult` MUST preserve `place_id`, `score`, and payload fields (`name`, `destination_id`) used by callers today. Fail-soft contracts from the existing indexing/search requirement remain in force: unavailable Qdrant or empty embedding short-circuits to `[]` without raising; Qdrant errors degrade to `[]`.

#### Scenario: Destination filter still applied
- **WHEN** `search_places(query, destination_id=A, top_k=N)` is invoked with Qdrant available and a non-empty embedding
- **THEN** the Qdrant query-points call includes a filter requiring payload `destination_id == A`

#### Scenario: Qdrant error returns empty list
- **WHEN** the query-points call raises
- **THEN** `search_places` returns `[]` and does not raise

#### Scenario: Empty embedding never calls Qdrant
- **WHEN** embedding returns an empty vector
- **THEN** `search_places` returns `[]` without calling query-points

#### Scenario: Pinned tests mock query-points
- **WHEN** the three search_places unit tests run
- **THEN** they assert against `query_points` (not the deprecated `search` method)
