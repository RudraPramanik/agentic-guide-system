## MODIFIED Requirements

### Requirement: Local compose remains development-only
The root `docker-compose.yml` (local PostGIS, Qdrant, Redis, and API) MUST remain documented as local development infra only and MUST NOT be prescribed as the production data plane.

#### Scenario: Blueprint separates dev and prod compose
- **WHEN** the blueprint describes containers on the VPS
- **THEN** it lists at most API + TLS proxy (optional compose), and directs data stores to hosted URLs
