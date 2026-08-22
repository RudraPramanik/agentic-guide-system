I think your concern is legitimate, but there's an important distinction:

Nominatim + OSRM are not really "places discovery" infrastructure.

Nominatim is primarily a geocoder/search engine, while OSRM is a routing engine. If your product's core promise is "find the best places to explore, then construct a route around them", you need a stronger POI discovery/enrichment layer. OSM data itself can be quite heterogeneous by geography.

So I wouldn't simply replace Nominatim. I'd change your geo architecture.

What I'd use for your prototype

I'd go:

                    Trip Planner
                         │
              ┌──────────┼──────────┐
              │          │          │
           Geocode      POI       Routing
              │          │          │
         Nominatim   Geoapify /    OSRM
              │      Overture
              │          │          │
              └──────────┼──────────┘
                         │
                    PostGIS
                         │
                    Qdrant later
My first choice: Geoapify for POIs

Geoapify is particularly interesting for your prototype because it provides geocoding + places + routing/isochrones and currently advertises a free tier of around 3,000 API calls/day.

So you could add:

GEOAPIFY_API_KEY=
GEOAPIFY_BASE_URL=

and implement:

class PlacesProvider(Protocol):
    async def search(
        self,
        lat: float,
        lon: float,
        radius: int,
        categories: list[str],
    ) -> list[Place]:
        ...

Then:

OverpassPlacesProvider
        +
GeoapifyPlacesProvider
        +
FutureGooglePlacesProvider

without changing your PlaceService.

But there's an even more interesting option: Overture

For Wandr specifically, I'd investigate Overture Maps Places very seriously.

Overture is an open geospatial dataset with tens of millions of POIs, and its Places dataset is designed specifically around structured place information. Current comparisons put it at roughly 53M+ POIs as an open dataset.

The important difference is:

Nominatim / OSM

"What's around here?"

vs.

Overture Places

"Give me a structured POI dataset I can search/rank/enrich."

That fits your architecture much better.

You don't necessarily need a live Overture API call for every user request. You can eventually:

Overture dataset
       ↓
ETL
       ↓
PostGIS
       ↓
Wandr POI database
       ↓
AI ranking

That is much closer to how I'd build your eventual product.

And this is where your architecture gets interesting

I would not make the LLM responsible for finding the "best places."

Instead:

User
 │
 ▼
Trip Planner
 │
 ▼
Candidate Retrieval
 │
 ├── OSM
 ├── Overture
 ├── Geoapify
 └── your DB
 │
 ▼
Candidate Normalization
 │
 ▼
Hard Filters
 │
 ▼
Ranking
 │
 ▼
LLM
 │
 ▼
Itinerary

The LLM should be deciding things like:

"Given these 30 candidate places, which combination best satisfies this user's preferences?"

It shouldn't be blindly asking:

"Give me good places in Darjeeling."

That change will massively improve the quality of your agent.

Your current Nominatim problem

Suppose the user says:

"Give me a relaxed afternoon in Darjeeling with good coffee and views."

Nominatim might give you geographic entities.

But your system needs:

Cafe A
Cafe B
Cafe C
Viewpoint A
Viewpoint B
Monastery A
Restaurant A
...

with attributes such as:

lat/lon
category
name
address
popularity proxy
opening hours
website
phone
source
OSM ID
confidence

That's POI retrieval, not simply geocoding.

I would actually keep Overpass

You currently have:

Nominatim
Overpass
OSRM

I wouldn't throw them away.

Instead make them specialized:

Nominatim
Place name → coordinates
coordinates → address
Overpass
OSM POI discovery
OSRM
A → B route
Geoapify
POI discovery / enrichment
Overture
large-scale structured POI dataset

That gives you a multi-source geo pipeline.

Don't blindly merge everything

This is important.

You don't want:

OSM → 30 places
Geoapify → 30 places
Overture → 30 places

= 90 places

Instead:

OSM
  ↓
Geoapify
  ↓
Overture
  ↓
Deduplication
  ↓
Entity resolution
  ↓
40 unique candidates

Use something like:

same coordinates
+
normalized name
+
distance threshold
+
category similarity
+
website/domain

to identify duplicates.

Then store:

{
  "place_id": "...",
  "name": "Keventers",
  "location": "...",
  "sources": [
    "osm",
    "geoapify",
    "overture"
  ]
}

This is actually excellent AI/data engineering practice for you to learn.

Then build a ranking layer

This is where Wandr can differentiate from generic map APIs.

Don't just return:

nearest places

Calculate:

PlaceScore =
    relevance
  + distance
  + popularity_proxy
  + category_match
  + opening_status
  + quality
  + user_preference
  + route_fit

For example:

             Candidate places
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   relevance     distance     quality
       │            │            │
       └────────────┼────────────┘
                    ▼
              Route fitness
                    │
                    ▼
             User preference
                    │
                    ▼
                 SCORE

That ranking layer is much more important to your product than which single POI API you use.

What about Mapbox?

If you are willing to use a free commercial tier, I'd also test Mapbox Search/Places.

Current 2026 comparisons report a free tier around 100K requests/month for some Mapbox geocoding/search usage, though the exact allowance depends on the API/product and account terms.

It's worth benchmarking against your current OSM pipeline.

For example, create:

POI Benchmark

Darjeeling
Dhaka
Bangkok
Tokyo
Paris
New York

and query:

cafes
restaurants
viewpoints
attractions
temples
museums
parks

Then compare:

Provider       Results   Unique   Useful   Coordinates   Metadata
OSM
Overpass
Geoapify
Mapbox
Overture

You'll discover very quickly which provider actually performs better for your target geography.

One thing I would NOT do

Don't replace:

Nominatim → Geoapify

and call the problem solved.

Your problem is probably retrieval quality, not merely the API.

Your architecture should become:

                 POI Sources
                     │
       ┌─────────────┼─────────────┐
       │             │             │
      OSM        Geoapify       Overture
       │             │             │
       └─────────────┼─────────────┘
                     ▼
              Normalization
                     ▼
               Deduplication
                     ▼
                PostGIS
                     ▼
             Candidate Retrieval
                     ▼
                  Ranking
                     ▼
                 LangGraph
                     ▼
                Itinerary

That's the architecture I'd recommend for Wandr.

For your current prototype

I'd make the smallest change:

Keep:

Nominatim
Overpass
OSRM

Add:

Geoapify Places

Then benchmark it.

If Geoapify significantly improves your target cities, keep it as a secondary provider. In parallel, start experimenting with Overture Places → PostGIS because that could eventually become your core POI data foundation.

And importantly, don't let this become provider-specific code. Your existing gateway abstraction is exactly what makes this easy:

class PlacesProvider(Protocol):
    ...

Then your planner can eventually use:

OSMPlacesProvider
GeoapifyPlacesProvider
OverturePlacesProvider

and your evaluation framework can tell you which combination actually produces better itineraries—not your intuition. That's exactly where your earlier goals of evals + context engineering + cost optimization start becoming real engineering rather than theory