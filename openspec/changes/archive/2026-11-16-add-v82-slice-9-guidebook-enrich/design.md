## Context

See proposal.md for why. `docs/steps/wandr_blueprint_version8.md` is the v8.2 target plan. §16 still defers accommodation and image providers. Slice 6 is the canonical place-id slice. Slice 7 is the optional reasoner and critic. Generate stays inside the existing 45-second ceiling. Lodging and photos are not in the planner graph today: Overpass asks for attractions, viewpoints, museums, and monasteries; `Place` has no media column; the Stay block is static copy.

This design is the edit map for that one document. It does not add modules.

## Goals / Non-Goals

**Goals:**

- The amended plan names Slice 9, its flags, contracts, honesty rules, and where it sits relative to Slices 6 and 7.
- A later implementer can read the blueprint and see that stays and photos are deterministic post-save work, not a new agent.

**Non-Goals:**

- Choosing a Wikimedia contact address, a cache TTL, or which frontend component file owns the Stay block. Those belong to the later implementation changes.
- Rewriting Slices 0–8 except the Slice 0.1 audit row and the cross-references listed below.

## Decisions

### 1. Amend the same file and retitle it v8.3

The heading, status line, and one-line summary change so a reader can see v8.2 plus Slice 9. The path stays `docs/steps/wandr_blueprint_version8.md`. v6.1 and v7 are not edited.

**Alternative:** a new `wandr_blueprint_version8_3.md`. Rejected. Two target plans would fork the slice order.

### 2. Slice 9 runs after Slice 6 and may run beside Slice 7

Entry line in §9: S0–S6 shipped, or at minimum 6.2 (canonical `place_id` and suggested-vs-routed) is in place. Slice 9 does not wait for the Slice 7 ship gate. The locked order diagram gains `S9` on a branch next to `S7`, both after `S6`.

**Alternative:** fold lodging and media into Slice 7. Rejected. Slice 7 is an LLM experiment with a license to stay off. Stays and photos are deterministic and must not depend on that experiment.

**Alternative:** run Slice 9 before Slice 6. Rejected. A photo or a stay attached to a place id that dedup later drops becomes a guidebook that cites a stop the trip no longer has.

### 3. Enrich sits under persistence, not inside the graph

§5.1 gains a branch under "Canonical trip persistence":

```text
saved trip
  ├─ [S9, LODGING_V1_ENABLED] lodging search inside SearchArea → suggested stays
  └─ [S9, MEDIA_ENRICH_ENABLED] media resolve per stop → credited photo or empty
```

§5.2 lists both as deterministic services. §5.3 adds `src/geo/media/` only. Lodging stays in the existing geo and places pipeline. No new planner tool, no new LLM role.

### 4. A stay is a place with category lodging, suggested until the user adds it

9.1 ingests Overpass `tourism=hotel|guest_house|hostel` inside the Slice 3 search area, through the existing place upsert, `category=lodging`. No lodging table.

9.2 writes `LodgingSuggestion` rows in the plan's contract language: `place_id`, name, lat, lng, category, `distance_to_base_km`, `price_status="unknown"`, `availability_status="unknown"`. Rank is distance to the trip base, then to that day's cluster. Status is `suggested`. A suggestion is not a stop and is not drawn as route geometry.

9.3 is optional and explicit: the user confirms one suggestion as the trip base, then the existing optimizer rebuilds the route. The plan does not auto-promote a hotel.

**Alternative:** a separate lodging domain and a second id space. Rejected. Slice 6's invariant is one id space. The parent media note already calls a new lodging domain the higher-churn option.

### 5. Photos use the geo facade, a JSONB cache, and a sibling read

9.4: `src/geo/media/` with a provider order of OSM `image` tag, then Wikimedia, then OpenTripMap. Cache on an additive `places.media` JSONB list of `PlaceMedia` (`url`, `source`, `attribution`, `fetched_at`). `source` is `osm`, `wikimedia`, or `opentripmap`.

9.5: additive `GET /api/v1/places/{id}/media` and `GET /api/v1/trips/{id}/media`, each `ApiResponse`. Empty list when nothing resolved. The plan marks these as proposed and subject to the Slice 0 "verify, do not invent" rule. They are not folded into `PlaceOut` in this amendment.

9.6: frontend contract only. The Stay block renders suggestions. A stop renders the media URL with a visible credit, or the existing gradient when the list is empty. Release of 9.6 needs a named frontend owner, same halt rule as 3.6 and 6.6. Backend may stay dark behind flags.

**Alternative:** put `media` on `PlaceOut` immediately. Rejected for the plan. It widens every place list before the cache is proven. A later ADR can fold it in.

**Alternative:** unlabeled stock photo when Commons misses. Rejected for stop cards. A destination hero may use a labeled stock image only if a later change asks for it; this amendment does not add that subslice.

### 6. Flags, budgets, and failure behavior the plan must state

| Flag | Default | Off means |
|---|---|---|
| `LODGING_V1_ENABLED` | `false` | Stay block keeps today's static copy |
| `MEDIA_ENRICH_ENABLED` | `false` | No media HTTP and no media reads on the request path |

Both go through `get_settings()`. No new mandatory key. `MEDIA_SOURCES` and `WIKIMEDIA_USER_AGENT` are proposed settings, added only when a later slice uses them. Reuse the existing OpenTripMap key if that source is already configured.

External calls, when a later slice implements them, follow the blueprint's resilience table: explicit timeout, tenacity retry, named fallback, never a 500. Lodging fallback is an empty suggestion list. Media fallback is an empty media list, and the UI keeps the gradient. A provider miss does not fail generate, because generate does not call them.

Generate replay with both flags off stays byte-identical. The 45-second ceiling is unchanged. §4 does not gain a lodging-count or photo-coverage gate.

### 7. Honesty rules, eval, guardrail, ADRs

New invariants, numbered after N10:

- N11. Media and lodging HTTP never run inside `POST /planner/generate`.
- N12. A stay suggestion is not a stop.
- N13. Price and availability stay `unknown` unless a source marks them verified. Slice 9 has no such source.
- N14. A photo with no attribution is not shown.
- N15. A stop with no photo keeps the non-photo fallback. Stock is not a photo of that place.

§11 adds honesty checks that inform and do not gate itinerary quality: no invented price, every suggestion has a `place_id`, a suggestion outside the search area is absent or the fallback is disclosed, attribution is present whenever a URL is present. Low photo coverage is a pass.

§10 gains one guardrail: `planner/service.py` and `travel_engine/` must not import the lodging client or `src/geo/media/`.

§15 adds: image URLs are untrusted data; Wikimedia calls send `WIKIMEDIA_USER_AGENT`; a media proxy, if a later slice adds one, uses the same SSRF rules as other provider URLs.

§21 adds ADR 015 (lodging source and unknown price) and ADR 016 (media facade, cache, attribution).

§8.1 adds the `places.media` column only. §8.5 points lodging at the existing cost label `unknown`.

§1 outcome table gains two rows sourced from Slice 9. §20 definition of done gains the two guidebook lines from the proposal. §16 drops the accommodation-and-image phrase and keeps the deferred list in the proposal. §0.1 audit gains `accommodation_label`, gradient cards, and the Stay copy.

### 8. Voice and the parent media note

Slice 9 is written in the same subslice table shape as Slices 1–7: goal, allowed paths, tests, verify, rollback, stop-if. Allowed paths are the future implementation's paths, marked proposed. Rollback for each subslice is the flag off, or revert the doc if the only change is this amendment.

One sentence points at `docs/context/free-media-map-guidebook.md` for the provider notes and the guidebook layout. The blueprint does not paste that catalog.

## Risks / Trade-offs

- [Readers treat v8.2's "Final" banner as still complete] → Retitle to v8.3 and say it amends v8.2. Do not leave the old banner over new slice text.
- [A later agent implements the proposed GET paths as if they exist] → Keep the document's existing rule: nothing is claimed present unless `blueprint_final.md`, `v2_blueprint.md`, or `.env.example` names it. Slice 9 endpoints and settings are proposed.
- [The parent media plan and this slice drift] → One pointer, no copied provider matrix. Map basemap toggles stay out of this file.
- [Photo coverage looks like a failed eval] → The plan states coverage is not a gate.
- [9.3 (confirm stay as trip base) couples lodging to the optimizer and slips into generate] → 9.3 is a user action on an existing trip, through the existing reoptimize path, and it is its own subslice.

## Migration Plan

1. Edit `docs/steps/wandr_blueprint_version8.md` per the decisions above.
2. Do not touch runtime config, migrations, or `docs/context.md`.
3. Rollback is reverting that file. No flag, deploy, or data migration belongs to this change.

## Open Questions

None. Provider contact details, cache TTL, and the frontend component split wait for the implementation changes and do not change this edit map.
