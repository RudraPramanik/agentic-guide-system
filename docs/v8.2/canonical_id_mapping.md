# Canonical trip id mapping (v8.3 Slice 6.1)

Read from the live models. This file does not add a second place id.

| Concept | Live symbol | Wire |
|---|---|---|
| Canonical place id | `places.id`, stored as `TripPlace.place_id` | GeoJSON point property `place_id`; `TripPlaceOut.place_id` |
| Stop row id | `TripPlace.id` | GeoJSON point property `trip_place_id`; `TripPlaceOut.id` |
| Day | `TripPlace.day_number` | GeoJSON `day`; `TripPlaceOut.day_number` |
| Route order | `TripPlace.order_in_day` for routed rows (`confirmed`, `user_added`) | GeoJSON `order`. Non-routed rows use `0` and are not a route position |
| Place name | `Place.name` | GeoJSON `name`. Narrative prose uses names |

`write_narrative` (`src/planner/graph/nodes/write_narrative.py`) writes day title and narrative text only. It must not invent place ids, coordinates, stop order, or times. UUID tokens in that prose that are not already on the schedule are stripped. There is no separate guide-agent UI (`docs/v8.2/repository_audit.md` §4). The trip page is the guide surface: routed stops, suggestions, and the map.

Suggestions are `TripPlace` rows with `stop_status=suggested` and the same `place_id`. They are not a second list and they do not enter route geometry until `POST /api/v1/trips/{id}/days/{day}/stops`.

Sibling changes:

- Frontend selection and captions: `v83-slice-6-6-trip-map-selection` (guideagent-frontend)
- Parent vault routing: `v83-slice-6-canonical-trip-boundary` (tripplanner)

`CANONICAL_TRIP_V2_ENABLED` defaults to false. While it is false, trip JSON and GeoJSON omit `stop_status`, `geometry_provenance`, and `version`.
