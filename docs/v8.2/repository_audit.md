# Repository audit (v8.3 Slice 0.1)

Read 2026-11-17. Evidence is source and tests. `docs/context.md` progress rows are not evidence.

Worktree at the start of this write: `docs/steps/wandr_blueprint_version8.md` was already modified, and `openspec/changes/v83-slice-0-1-repository-audit/` plus `openspec/changes/archive/2026-11-16-add-v82-slice-9-guidebook-enrich/` were already untracked. No `src/` or `tests/` files were dirty. This audit does not change them.

Status values: `implemented-tested`, `implemented-untested`, `partial`, `stub`, `deferred`.

## 1. Status matrix

### Inherited runtime

| Area | Status | Path | Symbol | Test |
|---|---|---|---|---|
| Settings | implemented-tested | `src/config.py` | `get_settings` | `tests/core/test_settings_boot.py::test_get_settings_boots_without_llm_api_key` |
| LLM gateway | implemented-tested | `src/core/llm/client.py` | `chat_completion`, `chat_with_tools` | `tests/core/test_llm_chat_with_tools.py::test_chat_with_tools_parses_tool_call` |
| Geocoder | implemented-tested | `src/geo/geocoder.py` | `geocode` | `tests/geo/test_geocoder.py::test_geocode_success` |
| Overpass | implemented-tested | `src/geo/overpass.py` | `fetch_pois` | `tests/geo/test_overpass.py::test_fetch_pois_failure_returns_empty` |
| OSRM | implemented-tested | `src/geo/osrm.py` | `get_route` | `tests/geo/test_osrm.py::test_get_route_fallback_when_osrm_none` |
| POI facade | implemented-tested | `src/geo/places.py` | `fetch_destination_pois` | `tests/geo/test_places.py::test_facade_default_overpass_only` |
| OpenTripMap gateway | implemented-untested | `src/geo/opentripmap.py` | `fetch_opentripmap_pois` | no test |
| Geoapify gateway | implemented-untested | `src/geo/geoapify_places.py` | `fetch_geoapify_pois` | no test |
| Country normalize | implemented-tested | `src/geo/country.py` | `normalize_country` | `tests/destinations/test_destinations_resolve.py::test_normalize_and_match_country` |
| Place model | implemented-tested | `src/places/models.py` | `Place` | `tests/places/test_places_model.py::test_tags_and_enriched_tags_are_distinct_columns` |
| Place upsert | implemented-untested | `src/places/repository.py` | `PlaceRepository.upsert_from_poi` | no test |
| Place radius search | implemented-tested | `src/places/repository.py` | `PlaceRepository.find_within_radius` | `tests/places/test_places_repository.py::test_find_within_radius_respects_geography_units` |
| Place HTTP | implemented-tested | `src/places/router.py` | `list_places`, `get_place` | `tests/places/test_places_router.py::test_list_places_paginated` |
| Place enrich | implemented-tested | `src/places/service.py` | `PlaceService.enrich_place` | `tests/places/test_place_enrichment.py::test_enrich_place_filters_vocab_and_never_writes_tags` |
| Readiness function | implemented-tested | `src/destinations/readiness.py` | `compute_readiness` | `tests/destinations/test_readiness.py::test_compute_readiness_ready` |
| Destination readiness | implemented-tested | `src/destinations/service.py` | `DestinationService.get_readiness` | `tests/destinations/test_readiness_integration.py::test_get_readiness_reaches_ready_when_qdrant_up` |
| Destination search | implemented-tested | `src/destinations/service.py` | `DestinationService.search` | `tests/destinations/test_destinations_service_search.py::test_search_geocode_none_raises_not_found` |
| Qdrant client | implemented-tested | `src/search/client.py` | `ensure_places_collection` | `tests/search/test_client.py::test_ensure_fail_soft_on_qdrant_error` |
| Place index | implemented-tested | `src/search/places_index.py` | `search_places` | `tests/search/test_places_index.py::test_search_places_includes_destination_filter` |
| Sparse encoder | implemented-tested | `src/search/sparse.py` | `encode_sparse` | `tests/search/test_sparse.py::test_encode_sparse_includes_name_tokens` |
| Embeddings | implemented-tested | `src/search/embeddings.py` | `embed_text` | `tests/search/test_embeddings.py::test_embed_text_returns_empty_when_unavailable` |

### Travel engine

Imports under `src/travel_engine/` are `__future__`, stdlib, `pydantic`, and sibling `src.travel_engine` modules. No `src.geo`, `httpx`, `sqlalchemy`, `qdrant`, or `litellm` import. `tests/travel_engine/test_purity.py::test_travel_engine_has_no_forbidden_imports` asserts that. `optimize_route` takes an injected `RoutingProvider`; the engine file does not call the network.

| Area | Status | Path | Symbol | Test |
|---|---|---|---|---|
| Protocols | implemented-tested | `src/travel_engine/protocols.py` | `RouteLeg`, `RoutingProvider` | `tests/travel_engine/test_route_optimizer.py::test_fake_matrix_complete_ordered_day` (uses `FakeRoutingProvider` against `RouteLeg`) |
| Rules | implemented-tested | `src/travel_engine/travel_rules.py` | `visit_duration_min` | `tests/travel_engine/test_travel_rules.py::test_duration_keys_cover_p2_categories` |
| Place selector | implemented-tested | `src/travel_engine/place_selector.py` | `select_places` | `tests/travel_engine/test_place_selector.py::test_multi_interest_outranks_single` |
| Day allocator | implemented-tested | `src/travel_engine/day_allocator.py` | `allocate_days` | `tests/travel_engine/test_day_allocator.py::test_never_more_than_max_places_per_day` |
| Route optimizer | implemented-tested | `src/travel_engine/route_optimizer.py` | `optimize_route` | `tests/travel_engine/test_route_optimizer.py::test_over_budget_records_dropped_stops` |
| Schedule builder | implemented-tested | `src/travel_engine/schedule_builder.py` | `build_day_schedule` | `tests/travel_engine/test_schedule_builder.py::test_viewpoint_lands_in_morning_slot` |
| Trip validator | implemented-tested | `src/travel_engine/trip_validator.py` | `validate_trip` | `tests/travel_engine/test_trip_validator.py::test_repeat_place_error` |

### Planner, trips, evaluation, ownership

| Area | Status | Path | Symbol | Test |
|---|---|---|---|---|
| Compiled graph | implemented-tested | `src/planner/graph/builder.py` | `build_planner_graph` | `tests/planner/test_tool_loop.py::test_happy_path_discover_to_wrap_up` |
| Tool registry | implemented-tested | `src/planner/tools/registry.py` | `TOOL_REGISTRY`, `execute_tool` | `tests/planner/test_tool_loop.py::test_wrong_phase_tool_not_called` |
| SSE generate | implemented-tested | `src/planner/router.py` | `sse_frame`, `TERMINAL_EVENTS` | `tests/planner/test_generate_sse.py::test_generate_single_terminal_when_spurious_second` |
| Terminal mapping | implemented-tested | `src/planner/emit_terminals.py` | `resolve_terminal_from_state` | `tests/planner/test_emit_terminals.py::test_success_itinerary_done_payload` |
| Save trip | implemented-tested | `src/trips/service.py` | `TripService.save_from_state` | `tests/trips/test_save_from_state.py::test_save_from_state_persists_base_prefs` |
| GeoJSON | implemented-tested | `src/trips/service.py` | `TripService.build_geojson` | `tests/trips/test_trips_http.py::test_geojson_points_only_when_no_polylines` |
| Trip edits | implemented-tested | `src/trips/service.py` | `reorder_stops`, `remove_stop`, `add_stop`, `reoptimize_day` | `tests/trips/test_edit_replan.py::test_reorder_updates_order_times_and_polylines` |
| Golden scorers | implemented-tested | `src/evaluation/scorers.py` | `score_case` | `tests/evaluation/test_scorers.py::test_score_case_deterministic` |
| Eval harness | implemented-untested | `scripts/run_evals.py` | `main` | no test |
| Generation record | implemented-tested | `src/evaluation/service.py` | `EvaluationService` | `tests/evaluation/test_token_usage_mapping.py::test_record_generation_maps_token_usage` |
| Guest ownership | implemented-tested | `src/trips/service.py` | `TripService.assert_can_access` | `tests/trips/test_save_from_state.py::test_assert_can_access_guest_and_owner` |
| Session cookie | implemented-tested | `src/auth/router.py` | `COOKIE_SESSION` (`"wandr_session"`) | `tests/trips/test_edit_replan.py::test_http_non_owner_returns_403` |

`Trip.session_id` is the column `assert_can_access` compares to that cookie (`src/trips/models.py`, `Trip.session_id`). `src/trips/router.py` reads it with `request.cookies.get(COOKIE_SESSION)`. Golden cases are on disk at `evals/golden/darjeeling/` (`dar-001` through `dar-012`). `scripts/run_evals.py` has no pytest of its own.

### Leftover packages

| Area | Status | Path | Symbol | Test |
|---|---|---|---|---|
| Scaffold app package | stub | `src/app/main.py` | `list_users` | no test |
| Scaffold app config | stub | `src/app/config.py` | file is empty | no test |
| Misspelled eval package | stub | `src/evalution/__init__.py` | file is empty | no test |

`src/app/main.py` returns static JSON from `list_users` and `create_user`. Nothing under `src/` imports `src.app` or `src.evalution`. The live app is `src/main.py`, which mounts auth, destinations, places, planner, and trips routers.

## 2. Settings inventory

`get_settings` loads `Settings` in `src/config.py`. "Both" means the name appears in `.env.example` (a commented example line still counts). Slice `shipped` means the field exists now. v8.3 names that are absent from `Settings` are `blueprint-only`.

### Shipped fields

| Name | Where | Default | Slice |
|---|---|---|---|
| `ENVIRONMENT` | both | `"development"` | shipped |
| `DEBUG` | both | `True` | shipped |
| `APP_VERSION` | Settings | `"1.0.0"` | shipped |
| `SECRET_KEY` | both | required, no default | shipped |
| `DATABASE_URL` | both | required, no default | shipped |
| `QDRANT_URL` | both | `"http://localhost:6335"` | shipped |
| `QDRANT_API_KEY` | both | `""` | shipped |
| `QDRANT_PLACES_COLLECTION` | both | `"places"` | shipped |
| `QDRANT_PLACES_COLLECTION_V2` | Settings | `"places_v2"` | shipped |
| `SEARCH_SPARSE_ENABLED` | both | `True` | shipped; example line is commented |
| `SEARCH_RRF_K` | Settings | `60` | shipped |
| `SEARCH_FUSION_DIAGNOSTICS` | both | `True` | shipped; example line is commented |
| `PLACES_EMBEDDING_BACKEND` | both | `"local"` | shipped |
| `PLACES_EMBEDDING_DIM` | both | `384` | shipped |
| `QDRANT_OPERATION_TIMEOUT_SECONDS` | both | `5.0` | shipped |
| `QDRANT_OPERATION_MAX_RETRIES` | both | `2` | shipped |
| `PLACES_EMBEDDING_MODEL` | both | `"sentence-transformers/all-MiniLM-L6-v2"` | shipped |
| `PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS` | both | `120.0` | shipped |
| `ENRICH_BATCH_LLM_CONCURRENCY` | both | `3` | shipped |
| `GEMINI_API_KEY` | both | `""` | shipped |
| `REDIS_URL` | both | `""` | shipped |
| `REDIS_CONNECT_TIMEOUT_SECONDS` | both | `1.0` | shipped |
| `REDIS_SOCKET_TIMEOUT_SECONDS` | both | `1.0` | shipped |
| `LLM_MODEL` | both | `"nvidia_nim/meta/llama-3.1-8b-instruct"` | shipped |
| `LLM_API_KEY` | both | `""` | shipped |
| `LLM_API_BASE` | both | `""` | shipped |
| `LLM_TIMEOUT_SECONDS` | both | `20` | shipped |
| `LLM_MAX_RETRIES` | both | `4` | shipped |
| `PLANNER_MAX_TOOL_CALLS` | both | `12` | shipped |
| `PLANNER_MAX_REPLAN_ATTEMPTS` | both | `2` | shipped |
| `PLANNER_GENERATION_TIMEOUT_SECONDS` | both | `45` | shipped |
| `PLANNER_MIN_READINESS_SCORE` | both | `0.3` | shipped |
| `PLANNER_AGENT_PHASE_STUCK_LIMIT` | both | `3` | shipped |
| `PLANNER_ABSOLUTE_MIN_PLACES` | Settings | `10` | shipped |
| `PLANNER_CACHE_TTL_SECONDS` | Settings | `3600` | shipped |
| `LANGFUSE_PUBLIC_KEY` | both | `""` | shipped |
| `LANGFUSE_SECRET_KEY` | both | `""` | shipped |
| `LANGFUSE_HOST` | both | `"https://cloud.langfuse.com"` (alias `LANGFUSE_BASE_URL`) | shipped |
| `NOMINATIM_USER_AGENT` | both | required, no default | shipped |
| `NOMINATIM_BASE_URL` | both | `"https://nominatim.openstreetmap.org"` | shipped |
| `NOMINATIM_API_KEY` | both | `""` | shipped |
| `OVERPASS_API_URL` | both | `"https://overpass-api.de/api/interpreter"` | shipped |
| `OSRM_BASE_URL` | both | `"https://router.project-osrm.org"` | shipped |
| `OSRM_MATRIX_MAX_CONCURRENCY` | both | `8` | shipped |
| `ROUTING_BACKEND` | both | `"haversine"` | shipped |
| `PLACES_SOURCES` | both | `"overpass"` | shipped |
| `OPENTRIPMAP_API_KEY` | both | `""` | shipped |
| `OPENTRIPMAP_BASE_URL` | both | `"https://api.opentripmap.com/0.1/en"` | shipped |
| `GEOAPIFY_API_KEY` | both | `""` | shipped |
| `GEOAPIFY_BASE_URL` | both | `"https://api.geoapify.com/v2"` | shipped |
| `ACCESS_TOKEN_EXPIRE_DAYS` | Settings | `7` | shipped |
| `GOOGLE_CLIENT_ID` | both | `""` | shipped |
| `GOOGLE_CLIENT_SECRET` | both | `""` | shipped |
| `GOOGLE_REDIRECT_URI` | both | `"http://localhost:8000/api/v1/auth/callback"` | shipped |
| `GOOGLE_AUTH_URL` | Settings | `"https://accounts.google.com/o/oauth2/v2/auth"` | shipped |
| `GOOGLE_TOKEN_URL` | Settings | `"https://oauth2.googleapis.com/token"` | shipped |
| `GOOGLE_USERINFO_URL` | Settings | `"https://www.googleapis.com/oauth2/v3/userinfo"` | shipped |
| `FRONTEND_URL` | both | `"http://localhost:3000"` | shipped |
| `RATE_LIMIT_DEFAULT_REQUESTS` | both | `60` | shipped |
| `RATE_LIMIT_DEFAULT_WINDOW_SECONDS` | both | `60` | shipped |
| `RATE_LIMIT_PLANNER_REQUESTS` | both | `10` | shipped |
| `RATE_LIMIT_PLANNER_WINDOW_SECONDS` | both | `60` | shipped |
| `RATE_LIMIT_PLANNER_PATH` | Settings | `"/api/v1/planner/generate"` | shipped |
| `RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS` | both | `20` | shipped |
| `RATE_LIMIT_DESTINATIONS_SEARCH_WINDOW_SECONDS` | both | `60` | shipped |
| `RATE_LIMIT_DESTINATIONS_SEARCH_PATH` | both | `"/api/v1/destinations/search"` | shipped |
| `RATE_LIMIT_DESTINATIONS_RESOLVE_REQUESTS` | Settings | `20` | shipped |
| `RATE_LIMIT_DESTINATIONS_RESOLVE_WINDOW_SECONDS` | Settings | `60` | shipped |
| `RATE_LIMIT_DESTINATIONS_RESOLVE_PATH` | Settings | `"/api/v1/destinations/resolve"` | shipped |
| `RATE_LIMIT_TRIP_EDIT_REQUESTS` | Settings | `20` | shipped |
| `RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS` | Settings | `60` | shipped |
| `RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS` | Settings | `5` | shipped |
| `RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS` | Settings | `60` | shipped |
| `DESTINATIONS_PREPARE_LOCK_TTL_SECONDS` | Settings | `180` | shipped |
| `DESTINATIONS_PREPARE_DEFAULT_RADIUS_KM` | Settings | `30.0` | shipped |
| `DESTINATIONS_PREPARE_MAX_RADIUS_KM` | Settings | `50.0` | shipped |
| `SEARCH_GEOCODE_TIMEOUT_SECONDS` | both | `8.0` | shipped |
| `CORS_ALLOWED_ORIGINS` | both | `["http://localhost:3000", "https://tripai-stagging.vercel.app"]` | shipped |

`.env.example` has no name that is missing from `Settings`. The local example assigns `CORS_ALLOWED_ORIGINS` to localhost only; the field default in `Settings` also includes the staging origin. Prepare's default radius is 30 km and is not in `.env.example`. Slice 3's "no hidden 30 km" target is about a future V2 path. Today's prepare default is this field.

### Blueprint §7 names

None of these are fields on `Settings`.

| Name | Where | Default | Slice |
|---|---|---|---|
| `RUN_TRACKING_ENABLED` | blueprint-only | absent | S1 |
| `LOCATION_V2_ENABLED` | blueprint-only | absent | S3 |
| `TRAVEL_ENGINE_V2_ENABLED` | blueprint-only | absent | S4 |
| `VALIDATOR_V2_ENFORCE` | blueprint-only | absent | S4 |
| `READINESS_V2_ENABLED` | blueprint-only | absent | S5 |
| `CANONICAL_TRIP_V2_ENABLED` | blueprint-only | absent | S6 |
| `REASONING_LAYER_ENABLED` | blueprint-only | absent | S7 |
| `REASONING_SHADOW_SAMPLE_RATE` | blueprint-only | absent | S7 |
| `EVALUATION_JUDGE_ENABLED` | blueprint-only | absent | S2 |
| `LODGING_V1_ENABLED` | blueprint-only | absent | S9 |
| `MEDIA_ENRICH_ENABLED` | blueprint-only | absent | S9 |
| `LOCATION_AUTO_RESOLVE_CONFIDENCE` | blueprint-only | absent | S3 |
| `LOCATION_POI_RADIUS_KM` | blueprint-only | absent | S3 |
| `LOCATION_NEIGHBORHOOD_RADIUS_KM` | blueprint-only | absent | S3 |
| `LOCATION_CITY_FALLBACK_RADIUS_KM` | blueprint-only | absent | S3 |
| `LOCATION_MAX_RADIUS_KM` | blueprint-only | absent | S3 |
| `READINESS_MIN_USABLE_PLACES_PER_DAY` | blueprint-only | absent | S5 |
| `READINESS_MIN_CATEGORIES` | blueprint-only | absent | S5 |
| `READINESS_MIN_CLUSTERS_MULTI_DAY` | blueprint-only | absent | S5 |
| `ORCHESTRATION_MAX_AGENT_INVOCATIONS` | blueprint-only | absent | S7 |
| `ORCHESTRATION_MAX_REPAIR_ATTEMPTS` | blueprint-only | absent | S7 |
| `AGENT_REASONING_MODEL` | blueprint-only | absent | S7 |
| `AGENT_CRITIC_MODEL` | blueprint-only | absent | S7 |
| `EVALUATION_JUDGE_TIMEOUT_SECONDS` | blueprint-only | absent | S2 |
| `MEDIA_SOURCES` | blueprint-only | absent | S9 |
| `WIKIMEDIA_USER_AGENT` | blueprint-only | absent | S9 |

`OPENTRIPMAP_API_KEY` is already shipped (see the table above). Slice 9 can reuse that key. It is not a new name.

## 3. SSE lifecycle

Emitters: `src/planner/router.py` (`sse_frame`, `TERMINAL_EVENTS`), `src/planner/service.py` (`PlannerService.generate`), `src/planner/emit_terminals.py` (`resolve_terminal_from_state`), plus `src/planner/graph/nodes/tool_executor.py` (`tool_executor_node`), `src/planner/graph/nodes/parse_preferences.py` (`parse_preferences`), and `src/planner/cache.py` (`_replay_cached`). Compared with `docs/FE_guide.md` §7.

| Event | Kind | Emitter | In FE guide §7 |
|---|---|---|---|
| `preferences_done` | progress | `parse_preferences`; cache replay | yes |
| `phase_changed` | progress | `tool_executor_node`; cache replay | yes |
| `tool_done` | progress | `tool_executor_node` | yes |
| `tool_batch_done` | progress | `tool_executor_node` | yes |
| `itinerary_done` | terminal | `resolve_terminal_from_state`; router yields it; cache replay | yes |
| `clarification_needed` | terminal | `resolve_terminal_from_state` | yes |
| `error` | terminal | `PlannerService.generate` (`generation_timeout`, `graph_recursion_limit`); `resolve_terminal_from_state` (`generation_aborted`); router safety net (`missing_terminal`) | yes. Guide names `generation_timeout` and `graph_recursion_limit` and allows any other string code |
| `tool_started` | not emitted | no `src/` emitter | named in the progress list |
| `validation_done` | not emitted | no `src/` emitter | named in the progress list |

`TERMINAL_EVENTS` is `itinerary_done`, `error`, `clarification_needed`. The router buffers those and yields exactly one. On `itinerary_done` it may add `trip_id` and `accommodation_label` before the frame.

### Pre-stream HTTP, not SSE

| Response | Kind | Symbol | Test |
|---|---|---|---|
| HTTP 409 `destination_not_ready` | pre-stream, no SSE body | `generate` in `src/planner/router.py` raises `DestinationNotReadyError` when `dest.place_count < PLANNER_ABSOLUTE_MIN_PLACES` | `tests/planner/test_generate_sse.py::test_generate_floor_place_count_zero_returns_409` |

`DestinationNotReadyError` sets `code="destination_not_ready"` in `src/destinations/exceptions.py`.

## 4. FE map and guide integration

Sibling repo, read only. Map contract in this repo: `docs/FE_guide.md` §15.

`TripPage` (`guideagent-frontend/features/trips/trip-page.tsx`) loads the trip, then mounts `TripDetail` and, when GeoJSON has features, `TripMap`. `TripMap` (`guideagent-frontend/features/trips/trip-map.tsx`) draws the FeatureCollection: Point layer `trip-points`, LineString layers `trip-lines` and `trip-lines-casing`. It does not invent coordinates.

`TripService.build_geojson` writes the same property names §15 lists: point `name`, `day`, `order`, `suggested_start_time`, `place_id`, `trip_place_id`; line `day`, `trip_id`. Coordinates are `[lng, lat]`.

### Guide-agent UI

No distinct guide-agent UI. Files checked: every `guideagent-frontend/features/**/*.tsx` (26 files), including `features/planner/progress-panel.tsx`, `features/planner/compose-form.tsx`, `features/planner/clarification-form.tsx`, `features/trips/trip-page.tsx`, `features/trips/trip-detail.tsx`, and `features/trips/trip-map.tsx`. None is a guide agent. The live surfaces are planner progress during generate, then the trip page (itinerary, eat picker, static stay copy, map).

## 5. Display-only stays and photos

| Surface | What the checkout shows | Path | Symbol |
|---|---|---|---|
| Stay label on generate | Optional string on the request. Comment in the model: display-only, not a `Trip` column. The router copies it onto the `itinerary_done` payload when it is set. It is not written by `save_from_state` as its own column. | `src/planner/schemas.py`; echo in `src/planner/router.py` | `PlanRequest.accommodation_label`; the `itinerary_done` branch that sets `data["accommodation_label"]` |
| Stay block on the trip page | Static sentence `Stays are unavailable.` under a Stay heading. No lodging query. | `guideagent-frontend/features/trips/trip-page.tsx` | `TripPage` |
| Stop card | One `<li>` per stop inside `TripDetail`. Classes: `rounded-xl border border-border/80 bg-card p-3.5 text-sm shadow-sm`. Text is order, name, optional start time, optional arrival note. No image and no gradient class. | `guideagent-frontend/features/trips/trip-detail.tsx` | `TripDetail` |
| Place media | `Place` columns are `osm_id`, `name`, `category`, `tags`, `enriched_tags`, `summary`, `location`, `destination_id`. No `media` field. | `src/places/models.py` | `Place` |
| Lodging table | No lodging table. Tables created in `migrations/versions/20260717_4251bc619373_create_all_tables.py` are `destinations`, `users`, `places`, `trips`, `trip_evaluations`, `trip_places`. Later migrations add `places.enriched_tags` and `trip_edit_events`. | `src/places/models.py` | `Place` (no lodging model) |

`_category_from_tags` in `src/geo/overpass.py` maps tourism, amenity, leisure, highway, historic, and natural tags onto attraction categories. It does not map `hotel`, `guest_house`, or `hostel`, and it never returns `lodging`.

These surfaces are not stay suggestions and not place photos. Slice 9 must not treat them as either.

## 6. Proposed v8 surface

Absent means the checkout has no symbol. Path is the file that was inspected. Status `deferred`. Test is `no test` for every row.

| Proposal | Status | Path | Symbol | Test |
|---|---|---|---|---|
| `location_intelligence/` | deferred | `src/` (no such package) | absent | no test |
| `planner/runs/` | deferred | `src/planner/` (no `runs/` package) | absent | no test |
| `src/geo/media/` | deferred | `src/geo/` (no `media/` package) | absent | no test |
| `planner_runs` table | deferred | `src/trips/models.py` | absent | no test |
| Unique idempotency key | deferred | `src/trips/models.py` | absent | no test |
| `trips.search_area` | deferred | `src/trips/models.py` `Trip` | absent | no test |
| `trips.discovery_anchor` | deferred | `src/trips/models.py` `Trip` | absent | no test |
| Stop status (`confirmed` / `suggested` / …) | deferred | `src/trips/models.py` `TripPlace` | absent | no test |
| `trips.version` | deferred | `src/trips/models.py` `Trip` | absent | no test |
| Feedback table | deferred | `src/evaluation/models.py` `TripEvaluation` | absent | no test |
| `places.media` | deferred | `src/places/models.py` `Place` | absent | no test |
| Lodging rows (`category=lodging`) | deferred | `src/geo/overpass.py` `_category_from_tags` | absent | no test |
| Each §7.1 flag and §7.2 knob in the inventory above | deferred | `src/config.py` `Settings` | absent | no test |

`Trip` stores `base_lat` / `base_lng` inside `preferences` JSON (`TripService.save_from_state`), not as `search_area` or `discovery_anchor`. `TripEvaluation` records generation quality (`user_saved`, `user_edited`, `tool_trace`). That is not a user-feedback table. `TripPlace` has `order_in_day` and no status field.

## 7. Contradiction log

| Blueprint section | Claim | Checkout | Path |
|---|---|---|---|
| §9 row 0.1 | Stop cards are gradient cards | Stop rows are solid `bg-card` borders. No gradient class on the stop `<li>`. Gradients exist on home, explore, and the places picker, not on trip stops. | `guideagent-frontend/features/trips/trip-detail.tsx` (`TripDetail`) |
| `docs/FE_guide.md` §7 progress list | `tool_started` and `validation_done` are progress events | No emitter under `src/` sends those names. Live progress names are `preferences_done`, `phase_changed`, `tool_done`, `tool_batch_done`. The same guide section says a run may omit `tool_started` / `validation_done`. `openspec/specs/planner-sse-generate/spec.md` still says those names MUST be included. | `src/planner/graph/nodes/tool_executor.py` `tool_executor_node`; `docs/FE_guide.md` §7 |

Audit continued after both rows. No ADR file was written.
