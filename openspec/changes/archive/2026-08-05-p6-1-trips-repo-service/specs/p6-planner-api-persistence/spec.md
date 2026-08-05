## MODIFIED Requirements

### Requirement: Trip persistence with Unit of Work and guest ownership
The system MUST implement `TripRepository` and `TripService.save_from_state(state, user_id, session_id) → Trip | None` such that Trip + TripPlace rows are written in **one transaction**. Partial TripPlace failure MUST roll back the entire save (no Trip without its places). Field mapping MUST follow the v2 locked mapping (including `TripPlace.polyline` from `leg_polyline`). Empty clarification/abort with no usable schedule MUST NOT create a Trip row (`None`).

Unauthenticated access to a trip MUST require the `wandr_session` cookie to **exactly match** `Trip.session_id`; mismatch or missing cookie MUST return **403** (same class of failure as an authenticated user accessing another user’s trip). Guests with matching session MAY access trips where `user_id IS NULL` prior to claim. Step **6.1** MUST deliver the service/repository/schemas/exceptions surface (`save_from_state`, `assert_can_access`, `claim_for_user`) unit-testable with a DB session and MUST NOT register trips HTTP routes.

The system MUST implement `TripService.claim_for_user(trip, user_id, session_id)`. `POST /api/v1/trips/{id}/claim` (`require_auth`) MUST be registered in step **6.3** (not 6.1): succeed only when `trip.user_id IS NULL` and session matches; otherwise **403** (session) or **409** (`TripAlreadyClaimedError`).

#### Scenario: Save then reload includes all stops
- **WHEN** `save_from_state` is called with a complete itinerary state
- **THEN** a Trip is returned and `get_with_places` returns every persisted stop

#### Scenario: Guest session mismatch is forbidden
- **WHEN** an unauthenticated client requests a trip whose `session_id` does not match `wandr_session`
- **THEN** the API returns HTTP 403 (not 404)

#### Scenario: Partial insert rolls back
- **WHEN** a TripPlace insert fails mid-save
- **THEN** no Trip row remains committed for that attempt

#### Scenario: Claim after login (service)
- **WHEN** `claim_for_user` is called with matching session on an unclaimed trip
- **THEN** `trip.user_id` equals that user after commit

#### Scenario: Re-claim is conflict
- **WHEN** claim is attempted on a trip that already has `user_id` set
- **THEN** `TripAlreadyClaimedError` is raised (HTTP 409 once the 6.3 route exists)

#### Scenario: Step 6.1 has no trips HTTP yet
- **WHEN** step 6.1 validation runs after trips service/repo land
- **THEN** `TripService` exposes `save_from_state` and `claim_for_user` and trips router endpoints are still unregistered
