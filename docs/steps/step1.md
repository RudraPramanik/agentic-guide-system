
# Wandr — P1 Cursor Prompts: Database Foundation + Auth
> Blueprint: `wandr_blueprint_v6.md` — Phase P1 (3 days · 9 blueprint steps)
> Expanded to **13 prompts** for solidity. New steps marked ★.
> Paste each prompt into Cursor **Agent mode** in order.
> Do NOT advance to the next prompt until the current ✅ validation passes.

---

## Expansion rationale

| Blueprint step | Prompt(s) |
|---|---|
| 1.1 — DB base + mixins | 1.1 (unchanged) |
| 1.2 — Session + engine | 1.2 (unchanged) |
| 1.3 — Alembic + PostGIS | 1.3 (unchanged) |
| 1.4 — All core models + migration 002 | **Split → 1.4a** User + Destination models · **1.4b** Place + Trip + TripPlace · **1.4c** TripEvaluation · **1.4d** Run migration 002 |
| 1.5 — BaseRepository | 1.5 (unchanged) |
| 1.6 — JWT + permissions | 1.6 (unchanged) |
| 1.7 — auth domain | **Split → 1.7a** schemas + exceptions · **1.7b** repository + service · **1.7c** router + main.py wiring |
| 1.8 — Request logging middleware | 1.8 (unchanged) |
| 1.9 — TripEditEvent migration 003 | 1.9 (unchanged) |
| ★ NEW | **1.10** — Rate limit middleware stub |
| ★ NEW | **1.11** — pytest harness + conftest.py + first tests |
| ★ NEW | **1.12** — P1 DB smoke test script |

**Why split 1.4:** Six models written in one Cursor pass produces silent schema mistakes on later models as context grows heavy. Splitting lets each group be validated before the migration runs — a bad migration is painful to undo.

**Why split 1.7:** Schemas/exceptions → repository → router enforces the layering constraint at the prompt level. One combined prompt almost always results in Cursor placing DB queries inside router functions.

**Why add 1.10–1.12:** Rate limit middleware belongs in P1 (not P6) because the middleware chain is being assembled now. The pytest harness must exist before P2 adds more domain code. The smoke test validates PostGIS geometry I/O and soft-delete filtering — things unit tests won't catch until a spatial query fails at runtime.

---

## Step 1.1 — core/database/base.py — Declarative Base + Mixins

```
Read AGENT.md before proceeding. Every line you write must comply with its rules.

TASK: Implement the SQLAlchemy declarative base and three reusable model mixins.
This is step 1.1. Install SQLAlchemy and asyncpg now.

─── INSTALL ───
Append to requirements.txt (with inline comments):
  sqlalchemy[asyncio]==2.0.31   # async ORM — step 1.1
  asyncpg==0.29.0               # async PostgreSQL driver — step 1.1

Install:
  pip install "sqlalchemy[asyncio]==2.0.31" asyncpg==0.29.0

─── IMPLEMENT src/core/database/base.py ───

Four things in this one file. Use SQLAlchemy 2.0 Mapped[] annotation style throughout.
Never use the old Column() API. Never use relationship() here — that comes when both sides exist.

1. Base — declarative base:
   from sqlalchemy.orm import DeclarativeBase
   class Base(DeclarativeBase):
       pass

2. UUIDMixin — primary key column shared by all models:
   - Column name: id
   - Type: sqlalchemy.dialects.postgresql.UUID(as_uuid=True)
   - Python default: uuid.uuid4  (callable, not called — so each instance gets its own UUID)
   - Rationale for Python-side default (not server_default): we need to know the ID before
     the INSERT completes, so FK references can be built in the same transaction.
   - primary_key=True

3. TimestampMixin — audit columns shared by all models:
   - created_at: Mapped[datetime], server_default=func.now(), nullable=False
   - updated_at: Mapped[datetime], server_default=func.now(), onupdate=func.now(), nullable=False
   - Both non-nullable — a row without timestamps is a bug.
   - Use server_default=func.now(), NOT Python datetime.utcnow() — DB sets the value,
     so it is consistent regardless of app server timezone.

4. SoftDeleteMixin — soft deletion marker:
   - deleted_at: Mapped[datetime | None], nullable=True, default=None
   - This mixin adds ONLY the column. No ORM events, no query hooks.
   - The filtering (WHERE deleted_at IS NULL) is the repository's responsibility.
   - Not every model uses this mixin — Trip, TripPlace, TripEditEvent, TripEvaluation,
     Destination do NOT use it. User and Place do.

─── RULES ───
- Do NOT define __abstract__ = True on Base itself.
- UUIDMixin.id default is uuid.uuid4 (Python callable), never server_default.
- TimestampMixin uses func.now() (server-side), never Python datetime.utcnow().
- SoftDeleteMixin has NO query logic — only the column definition.
- No imports of domain modules. This file has zero domain awareness.

─── VALIDATION ───
Run:
  python -c "
from src.core.database.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String

class _Check(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = '_check_table'
    name: Mapped[str] = mapped_column(String(50))

cols = {c.name for c in _Check.__table__.columns}
assert 'id' in cols, 'missing id'
assert 'created_at' in cols, 'missing created_at'
assert 'updated_at' in cols, 'missing updated_at'
assert 'deleted_at' in cols, 'missing deleted_at'
print('columns:', sorted(cols))
print('PASS — all mixin columns present')
"

Expected: PASS line with all five column names. No import errors.
```

---

## Step 1.2 — core/database/session.py — Async Engine + Pool + Connection Test

```
Read AGENT.md before proceeding.

TASK: Implement the async database engine, session factory, FastAPI dependency, and a connection test script.
This is step 1.2. No new package installs.

─── IMPLEMENT src/core/database/session.py ───

Three things:

1. Module-level async engine:
   from sqlalchemy.ext.asyncio import create_async_engine
   from src.config import get_settings

   engine = create_async_engine(
       get_settings().DATABASE_URL,
       pool_size=10,
       max_overflow=20,
       pool_pre_ping=True,    # recycles stale connections — mandatory for hosted Postgres
       pool_recycle=3600,     # recycle after 1 hour — prevents silent connection drops
       echo=get_settings().DEBUG,
   )

2. Module-level async session factory:
   from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

   AsyncSessionLocal = async_sessionmaker(
       bind=engine,
       class_=AsyncSession,
       expire_on_commit=False,   # prevents DetachedInstanceError after commit in async code
       autocommit=False,
       autoflush=False,
   )

3. get_db() — FastAPI async dependency generator:
   from typing import AsyncGenerator

   async def get_db() -> AsyncGenerator[AsyncSession, None]:
       async with AsyncSessionLocal() as session:
           try:
               yield session
           except Exception:
               await session.rollback()
               raise
           finally:
               await session.close()

4. get_engine() — returns the module-level engine (for lifespan, migrations, tests):
   def get_engine():
       return engine

─── UPDATE src/main.py lifespan ───
Replace any inline DB connection in the lifespan startup with:
   from src.core.database.session import get_engine
   from sqlalchemy import text
   async with get_engine().connect() as conn:
       await conn.execute(text("SELECT 1"))

─── CREATE scripts/test_db_conn.py ───
Standalone script — NOT a pytest test — verifies DB connection outside the app:

  import asyncio
  from sqlalchemy import text
  from src.core.database.session import get_engine

  async def main():
      engine = get_engine()
      async with engine.connect() as conn:
          row = (await conn.execute(text("SELECT version()"))).fetchone()
          print(f"  Connected: {row[0][:60]}...")
          db = (await conn.execute(text("SELECT current_database()"))).fetchone()
          print(f"  Database:  {db[0]}")
          pool = (await conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"))).fetchone()
          print(f"  Active connections: {pool[0]}")
      await engine.dispose()
      print("  Pool OK — connection test passed")

  if __name__ == "__main__":
      asyncio.run(main())

─── RULES ───
- pool_pre_ping=True is non-negotiable. Without it, connections dropped by Neon/Supabase after
  idle periods produce silent 500s on the first request after a quiet period.
- expire_on_commit=False is non-negotiable for async SQLAlchemy — accessing attributes after
  commit without this triggers lazy-load errors inside async context.
- get_db() MUST rollback before re-raising on exception. Open transactions block table locks.
- Never use sync Session or sync sessionmaker anywhere in this project.
- get_settings() is called at module import time here. If DATABASE_URL is missing from .env,
  this raises immediately on import — which is the correct fail-fast behaviour.

─── VALIDATION ───
Ensure Docker Postgres is running:
  docker compose up -d

Run:
  python scripts/test_db_conn.py

Expected:
  Connected: PostgreSQL 16.x on x86_64-pc-linux-gnu ...
  Database:  wandr
  Active connections: 1
  Pool OK — connection test passed
```

---

## Step 1.3 — Alembic + Migration 001: PostGIS

```
Read AGENT.md before proceeding.

TASK: Configure Alembic for async SQLAlchemy and run the first migration to enable PostGIS.
This is step 1.3. Install alembic and geoalchemy2 now.

─── INSTALL ───
Append to requirements.txt:
  alembic==1.13.2       # database migrations — step 1.3
  geoalchemy2==0.15.2   # PostGIS geometry types for SQLAlchemy — step 1.3

Install:
  pip install alembic==1.13.2 geoalchemy2==0.15.2

─── CONFIGURE alembic.ini ───
Replace the placeholder content with a real config. Key settings:
  script_location = alembic
  file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
  timezone = UTC
  prepend_sys_path = .

Do NOT set sqlalchemy.url in alembic.ini — it is injected at runtime from get_settings().

─── IMPLEMENT alembic/env.py ───
Must support async SQLAlchemy. Full implementation below — replace the placeholder entirely:

  from logging.config import fileConfig
  from sqlalchemy import pool
  from sqlalchemy.engine import Connection
  from sqlalchemy.ext.asyncio import async_engine_from_config
  from alembic import context

  from src.core.database.base import Base
  from src.config import get_settings

  # ── Model imports ── add each new models.py here as domains are implemented ──
  # (empty until step 1.4a)

  config = context.config
  if config.config_file_name is not None:
      fileConfig(config.config_file_name)

  # Inject DATABASE_URL from environment — never read from alembic.ini
  config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

  target_metadata = Base.metadata


  def run_migrations_offline() -> None:
      url = config.get_main_option("sqlalchemy.url")
      context.configure(
          url=url,
          target_metadata=target_metadata,
          literal_binds=True,
          dialect_opts={"paramstyle": "named"},
      )
      with context.begin_transaction():
          context.run_migrations()


  def do_run_migrations(connection: Connection) -> None:
      context.configure(connection=connection, target_metadata=target_metadata)
      with context.begin_transaction():
          context.run_migrations()


  async def run_async_migrations() -> None:
      connectable = async_engine_from_config(
          config.get_section(config.config_ini_section, {}),
          prefix="sqlalchemy.",
          poolclass=pool.NullPool,
      )
      async with connectable.connect() as connection:
          await connection.run_sync(do_run_migrations)
      await connectable.dispose()


  def run_migrations_online() -> None:
      import asyncio
      asyncio.run(run_async_migrations())


  if context.is_offline_mode():
      run_migrations_offline()
  else:
      run_migrations_online()

─── CREATE alembic/versions/001_enable_postgis.py ───
Create this file manually (not autogenerated). Set these attributes:
  revision = "001"
  down_revision = None
  branch_labels = None
  depends_on = None

  def upgrade() -> None:
      op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
      op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
      op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

  def downgrade() -> None:
      pass   # extensions are not dropped — they may be shared

─── RULES ───
- alembic upgrade head is NEVER called inside app startup code. Deploy step only.
- Do not put Python model classes inside migration files. Migrations use op.create_table()
  or raw SQL only.
- The model imports block in env.py starts empty. It MUST be updated every time a new
  models.py file is created — autogenerate only sees models that are imported.
- uuid-ossp gives gen_random_uuid() — needed for raw SQL in seed scripts.

─── VALIDATION ───
Run:
  alembic upgrade head

Expected output contains:
  Running upgrade  -> 001, Enable PostGIS extensions

Verify extensions installed:
  docker exec wandr_postgres psql -U wandr -d wandr -c "\dx"

Expected: postgis, postgis_topology, and uuid-ossp all appear in the list.
```

---

## Step 1.4a — User + Destination Models

```
Read AGENT.md before proceeding.

TASK: Implement the User and Destination SQLAlchemy models.
This is step 1.4a — first of four model steps. No package installs.

─── IMPLEMENT src/auth/models.py ───

  import uuid
  from datetime import datetime
  from sqlalchemy import String, Boolean
  from sqlalchemy.orm import Mapped, mapped_column
  from sqlalchemy.dialects.postgresql import UUID as PgUUID
  from src.core.database.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin

  class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
      __tablename__ = "users"

      email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
      name: Mapped[str] = mapped_column(String(255), nullable=False)
      avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
      google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
      is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

      def __repr__(self) -> str:
          return f"<User id={self.id} email={self.email}>"

─── IMPLEMENT src/destinations/models.py ───
Destination caches Nominatim geocode results and tracks data-readiness counters
(place_count, enriched_count, indexed_count) that the readiness endpoint reads.
These counters are denormalized — updated by seed scripts, not by FK count queries.
Destination does NOT use SoftDeleteMixin — destinations are never soft-deleted.

  import uuid
  from sqlalchemy import String, Float, Integer
  from sqlalchemy.orm import Mapped, mapped_column
  from src.core.database.base import Base, UUIDMixin, TimestampMixin

  class Destination(Base, UUIDMixin, TimestampMixin):
      __tablename__ = "destinations"

      name: Mapped[str] = mapped_column(String(255), nullable=False)
      country: Mapped[str] = mapped_column(String(100), nullable=False)
      display_name: Mapped[str] = mapped_column(String(512), nullable=False)
      osm_place_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
      lat: Mapped[float] = mapped_column(Float, nullable=False)
      lng: Mapped[float] = mapped_column(Float, nullable=False)

      # Readiness counters — updated by seed/enrich scripts, not by FK aggregates
      place_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
      enriched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
      indexed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

      def __repr__(self) -> str:
          return f"<Destination id={self.id} name={self.name}>"

─── UPDATE alembic/env.py ───
Add to the model imports block:
  from src.auth.models import User           # noqa: F401
  from src.destinations.models import Destination  # noqa: F401

─── RULES ───
- Use SQLAlchemy 2.0 Mapped[] annotation style. No Column() calls.
- google_id is nullable — users may exist without Google OAuth.
- Do NOT add relationship() yet — both sides must exist before relationships are defined.
- No foreign keys in this step — User and Destination reference nothing yet.

─── VALIDATION ───
Run:
  python -c "
from src.auth.models import User
from src.destinations.models import Destination

u_cols = {c.name for c in User.__table__.columns}
d_cols = {c.name for c in Destination.__table__.columns}
print('User cols:', sorted(u_cols))
print('Destination cols:', sorted(d_cols))

assert {'id','email','name','google_id','is_active','deleted_at','created_at','updated_at'} <= u_cols
assert {'id','name','country','lat','lng','place_count','enriched_count','indexed_count'} <= d_cols
print('PASS')
"

Expected: PASS, all asserted columns present.
```

---

## Step 1.4b — Place + Trip + TripPlace Models

```
Read AGENT.md before proceeding.

TASK: Implement Place, Trip, and TripPlace models. These have PostGIS geometry, JSONB, enums,
and composite indexes that must be exactly right.
This is step 1.4b. No package installs.

─── IMPLEMENT src/places/models.py ───

  import uuid
  from typing import Any
  from sqlalchemy import String, Text, Index, ForeignKey
  from sqlalchemy.orm import Mapped, mapped_column
  from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
  from geoalchemy2 import Geometry
  from src.core.database.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin

  class Place(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
      __tablename__ = "places"

      osm_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
      name: Mapped[str] = mapped_column(String(512), nullable=False)
      category: Mapped[str] = mapped_column(String(100), nullable=False)
      tags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
      summary: Mapped[str | None] = mapped_column(Text, nullable=True)

      # PostGIS POINT — SRID 4326 = WGS84 (standard GPS coordinates)
      location: Mapped[Any] = mapped_column(
          Geometry(geometry_type="POINT", srid=4326),
          nullable=False,
      )

      destination_id: Mapped[uuid.UUID] = mapped_column(
          PgUUID(as_uuid=True),
          ForeignKey("destinations.id", ondelete="CASCADE"),
          nullable=False,
          index=True,
      )

      __table_args__ = (
          Index("ix_places_destination_category", "destination_id", "category"),
      )

      def __repr__(self) -> str:
          return f"<Place id={self.id} name={self.name} category={self.category}>"

─── IMPLEMENT src/trips/models.py ───
Include TripStatus enum, Trip, and TripPlace in this one file.

  import uuid
  import enum
  from typing import Any
  from sqlalchemy import String, Integer, Index, ForeignKey, UniqueConstraint, Enum as SAEnum
  from sqlalchemy.orm import Mapped, mapped_column
  from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
  from src.core.database.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin

  class TripStatus(str, enum.Enum):
      DRAFT    = "draft"
      COMPLETE = "complete"
      FAILED   = "failed"

  class Trip(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
      __tablename__ = "trips"

      # One of user_id or session_id always identifies the owner
      user_id: Mapped[uuid.UUID | None] = mapped_column(
          PgUUID(as_uuid=True),
          ForeignKey("users.id", ondelete="SET NULL"),
          nullable=True,
          index=True,
      )
      session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
      destination_id: Mapped[uuid.UUID] = mapped_column(
          PgUUID(as_uuid=True),
          ForeignKey("destinations.id", ondelete="RESTRICT"),
          nullable=False,
          index=True,
      )
      days: Mapped[int] = mapped_column(Integer, nullable=False)
      preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
      status: Mapped[TripStatus] = mapped_column(
          SAEnum(TripStatus, name="trip_status"),
          default=TripStatus.DRAFT,
          nullable=False,
      )

      __table_args__ = (
          Index("ix_trips_user_created", "user_id", "created_at"),
      )

      def __repr__(self) -> str:
          return f"<Trip id={self.id} status={self.status} days={self.days}>"

  class TripPlace(Base, UUIDMixin, TimestampMixin):
      """One row per stop per day in a trip. No SoftDeleteMixin — stops are hard-deleted."""
      __tablename__ = "trip_places"

      trip_id: Mapped[uuid.UUID] = mapped_column(
          PgUUID(as_uuid=True),
          ForeignKey("trips.id", ondelete="CASCADE"),
          nullable=False,
      )
      place_id: Mapped[uuid.UUID] = mapped_column(
          PgUUID(as_uuid=True),
          ForeignKey("places.id", ondelete="RESTRICT"),
          nullable=False,
      )
      day_number: Mapped[int] = mapped_column(Integer, nullable=False)
      order_in_day: Mapped[int] = mapped_column(Integer, nullable=False)
      travel_time_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
      visit_duration_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
      suggested_start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "HH:MM"
      arrival_note: Mapped[str | None] = mapped_column(String(512), nullable=True)
      polyline: Mapped[str | None] = mapped_column(Text, nullable=True)  # encoded route leg

      __table_args__ = (
          Index("ix_trip_places_trip_day", "trip_id", "day_number"),
          UniqueConstraint("trip_id", "place_id", name="uq_trip_place"),
      )

      def __repr__(self) -> str:
          return f"<TripPlace trip={self.trip_id} day={self.day_number} order={self.order_in_day}>"

─── UPDATE alembic/env.py ───
Add to the model imports block:
  from src.places.models import Place                    # noqa: F401
  from src.trips.models import Trip, TripPlace, TripStatus  # noqa: F401

─── RULES ───
- Geometry column MUST specify geometry_type="POINT" and srid=4326 explicitly.
  Generic Geometry without these breaks ST_DWithin radius queries.
- TripStatus MUST be str enum (class TripStatus(str, enum.Enum)) — serialises cleanly to JSON.
- TripPlace has NO SoftDeleteMixin — stops are hard-deleted. Edit history is in TripEditEvent.
- UniqueConstraint(trip_id, place_id) prevents the same place appearing twice in one trip.
- All ForeignKey ondelete values are intentional — do not change them.
- JSONB columns with dict/list defaults use callable defaults (default=dict, default=list),
  never default={} or default=[].

─── VALIDATION ───
Run:
  python -c "
from src.places.models import Place
from src.trips.models import Trip, TripPlace, TripStatus

p = {c.name for c in Place.__table__.columns}
t = {c.name for c in Trip.__table__.columns}
tp = {c.name for c in TripPlace.__table__.columns}

assert 'location' in p, 'Place.location missing'
assert 'osm_id' in p, 'Place.osm_id missing'
assert 'session_id' in t, 'Trip.session_id missing'
assert 'preferences' in t, 'Trip.preferences missing'
assert 'order_in_day' in tp, 'TripPlace.order_in_day missing'
assert 'suggested_start_time' in tp, 'TripPlace.suggested_start_time missing'
assert 'polyline' in tp, 'TripPlace.polyline missing'
print('Place cols:', sorted(p))
print('TripPlace cols:', sorted(tp))
print('PASS')
"

Expected: PASS, all asserted columns present.
```

---

## Step 1.4c — TripEvaluation Model

```
Read AGENT.md before proceeding.

TASK: Implement TripEvaluation — the append-only quality and observability record written
after every planner generation run.
This is step 1.4c. No package installs.

─── IMPLEMENT src/evaluation/models.py ───
Every field maps exactly to the TripEvaluation schema in the blueprint.
No SoftDeleteMixin — evaluations are append-only, never deleted.

  import uuid
  from datetime import datetime
  from sqlalchemy import String, Integer, Float, Boolean, Text, Index, ForeignKey
  from sqlalchemy.orm import Mapped, mapped_column
  from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
  from src.core.database.base import Base, UUIDMixin, TimestampMixin

  class TripEvaluation(Base, UUIDMixin, TimestampMixin):
      __tablename__ = "trip_evaluations"

      # ── Linkage ──
      trip_id: Mapped[uuid.UUID | None] = mapped_column(
          PgUUID(as_uuid=True), ForeignKey("trips.id", ondelete="SET NULL"),
          nullable=True, index=True,
      )
      destination_id: Mapped[uuid.UUID] = mapped_column(
          PgUUID(as_uuid=True), ForeignKey("destinations.id", ondelete="RESTRICT"),
          nullable=False, index=True,
      )

      # ── Input ──
      raw_input: Mapped[str] = mapped_column(Text, nullable=False)
      parsed_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

      # ── Pipeline counts ──
      candidates_retrieved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
      candidates_after_ranking: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

      # ── Output snapshot ──
      final_route: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
      places_per_day: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
      total_distance_km: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
      base_lat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
      base_lng: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

      # ── Performance ──
      generation_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
      token_usage: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
      llm_model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
      llm_retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

      # ── Agent loop signals ──
      tool_loop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
      tool_trace: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
      agent_phase_reached: Mapped[str] = mapped_column(String(50), default="discover", nullable=False)
      readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)

      # ── Resilience signals ──
      used_geo_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
      used_osrm_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
      abort_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

      # ── Quality signals (written after user interaction) ──
      validation_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
      validation_warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
      user_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
      user_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

      __table_args__ = (
          Index("ix_trip_eval_dest_created", "destination_id", "created_at"),
          Index("ix_trip_eval_abort", "abort_triggered"),  # for operational alerting queries
      )

      def __repr__(self) -> str:
          return f"<TripEvaluation id={self.id} abort={self.abort_triggered}>"

─── UPDATE alembic/env.py ───
Add to the model imports block:
  from src.evaluation.models import TripEvaluation  # noqa: F401

─── RULES ───
- tool_trace is JSONB list — it can be large on complex trips; never VARCHAR.
- The abort_triggered index exists specifically for the operational query
  "show me all recent generations that hit the ceiling" — a critical alert signal.
- JSONB list columns (places_per_day, tool_trace, validation_warnings) use default=list
  (callable), never default=[].
- No SoftDeleteMixin — evaluations are evidence records, never deleted.

─── VALIDATION ───
Run:
  python -c "
from src.evaluation.models import TripEvaluation

cols = {c.name for c in TripEvaluation.__table__.columns}
required = {
    'id','trip_id','destination_id','raw_input','parsed_preferences',
    'candidates_retrieved','candidates_after_ranking',
    'final_route','places_per_day','total_distance_km','base_lat','base_lng',
    'generation_time_ms','token_usage','llm_model','llm_retry_count',
    'tool_loop_count','tool_trace','agent_phase_reached','readiness_score',
    'used_geo_fallback','used_osrm_fallback','abort_triggered',
    'validation_passed','validation_warnings','user_saved','user_edited',
    'created_at','updated_at',
}
missing = required - cols
assert not missing, f'Missing columns: {missing}'
print('All', len(cols), 'columns present')
print('PASS')
"

Expected: PASS, column count printed (should be 28+). No missing columns.
```

---

## Step 1.4d — Run Migration 002: Create All Tables

```
Read AGENT.md before proceeding.

TASK: Generate and run migration 002 that creates all core tables defined in steps 1.4a–1.4c.
This is step 1.4d. No package installs.

─── PRE-CHECK ───
Confirm alembic/env.py has all five model imports:
  from src.auth.models import User                           # noqa: F401
  from src.destinations.models import Destination            # noqa: F401
  from src.places.models import Place                        # noqa: F401
  from src.trips.models import Trip, TripPlace, TripStatus  # noqa: F401
  from src.evaluation.models import TripEvaluation          # noqa: F401

If any are missing, add them now before generating the migration.

─── GENERATE MIGRATION ───
  alembic revision --autogenerate -m "create_all_tables"

─── REVIEW THE GENERATED FILE BEFORE RUNNING ───
Open the generated file in alembic/versions/ and verify:

Required tables (6 total):
  [ ] users
  [ ] destinations
  [ ] places
  [ ] trips
  [ ] trip_places
  [ ] trip_evaluations

Required on places table:
  [ ] location column uses Geometry type (not Text or VARCHAR)
  [ ] destination_id ForeignKey present

Required on trips table:
  [ ] trip_status enum type defined before the table
  [ ] user_id nullable ForeignKey to users
  [ ] session_id String column with index

Required on trip_places table:
  [ ] UniqueConstraint on (trip_id, place_id) present
  [ ] suggested_start_time String(5) column present
  [ ] polyline Text column present

Required on trip_evaluations table:
  [ ] tool_trace JSONB column present
  [ ] abort_triggered Boolean with index present
  [ ] All 28+ columns from 1.4c present

If the Geometry column appears as VARCHAR or Text in the migration — STOP.
This means geoalchemy2 isn't registered. Fix by ensuring geoalchemy2 is imported
in env.py: add "import geoalchemy2" at the top of alembic/env.py.

─── RUN MIGRATION ───
Once the review passes:
  alembic upgrade head

─── RULES ───
- Never run alembic upgrade head before reviewing the generated file.
- If the autogenerated migration is wrong, delete it and fix the model before regenerating.
- A bad migration is much harder to fix than a bad model definition.

─── VALIDATION ───
Run:
  docker exec wandr_postgres psql -U wandr -d wandr -c "\dt"

Expected: 6 tables listed (users, destinations, places, trips, trip_places, trip_evaluations).

Run:
  docker exec wandr_postgres psql -U wandr -d wandr -c "\di"

Expected: All indexes from __table_args__ present, plus automatic index on places.location (PostGIS spatial index).

Run:
  docker exec wandr_postgres psql -U wandr -d wandr -c "SELECT typname FROM pg_type WHERE typname = 'trip_status';"

Expected: one row — trip_status.

Run:
  alembic current

Expected: shows revision ID with "(head)" label.
```

---

## Step 1.5 — core/database/base_repository.py — Generic Repository Base

```
Read AGENT.md before proceeding.

TASK: Implement the generic repository base class. Every domain repository inherits from this.
This encodes the Generic Repository + Specification Pattern from the blueprint.
This is step 1.5. No package installs.

─── IMPLEMENT src/core/database/base_repository.py ───

The class signature: BaseRepository(Generic[ModelT, IDT])
Concrete repos declare: class UserRepo(BaseRepository[User, uuid.UUID]): pass

Implement every method completely — no stubs, no pass bodies.

  import uuid
  from typing import Generic, TypeVar, Type, Any, TYPE_CHECKING
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select, func, true, update as sa_update
  from sqlalchemy.orm import DeclarativeBase
  from datetime import datetime

  from src.core.exceptions import NotFoundError

  if TYPE_CHECKING:
      from src.core.pagination import PageParams

  ModelT = TypeVar("ModelT", bound=DeclarativeBase)
  IDT = TypeVar("IDT")


  class BaseRepository(Generic[ModelT, IDT]):

      def __init__(self, session: AsyncSession) -> None:
          self.session = session

      # ── Model class resolution ──

      @property
      def model_class(self) -> Type[ModelT]:
          """
          Resolves the concrete model class from the Generic[ModelT, IDT] type parameters.
          Works for both direct instantiation and subclass instantiation.
          """
          import typing
          orig = getattr(self.__class__, "__orig_bases__", [])
          for base in orig:
              args = typing.get_args(base)
              if args:
                  return args[0]
          raise TypeError(f"Cannot resolve model_class for {self.__class__.__name__}")

      def _soft_delete_filter(self):
          """
          Returns a WHERE clause fragment for soft-delete filtering.
          If the model has deleted_at (SoftDeleteMixin): WHERE deleted_at IS NULL
          If the model has no deleted_at: returns sqlalchemy true() — no filter applied.
          """
          if hasattr(self.model_class, "deleted_at"):
              return self.model_class.deleted_at.is_(None)
          return true()

      # ── Read ──

      async def get_by_id(self, id: IDT) -> ModelT | None:
          """Return model by primary key, or None if not found or soft-deleted."""
          stmt = select(self.model_class).where(
              self.model_class.id == id,
              self._soft_delete_filter(),
          )
          result = await self.session.execute(stmt)
          return result.scalar_one_or_none()

      async def get_by_id_or_raise(self, id: IDT) -> ModelT:
          """Return model by primary key or raise NotFoundError (404)."""
          obj = await self.get_by_id(id)
          if obj is None:
              raise NotFoundError(
                  message=f"{self.model_class.__name__} not found",
                  details={"id": str(id)},
              )
          return obj

      async def exists(self, **kwargs: Any) -> bool:
          """Return True if any non-deleted record matches all kwargs as equality filters."""
          stmt = select(self.model_class.id).where(
              self._soft_delete_filter(),
              *[getattr(self.model_class, k) == v for k, v in kwargs.items()],
          )
          result = await self.session.execute(stmt)
          return result.first() is not None

      async def list_paginated(
          self,
          filters: dict[str, Any],
          params: "PageParams",
          order_by_col: Any = None,
          order_desc: bool = True,
      ) -> tuple[list[ModelT], int]:
          """
          Returns (items_for_this_page, total_count_matching_filters).
          filters: {column_name: value} — exact-match equality only (Specification Pattern).
          Automatically excludes soft-deleted rows.
          """
          base_stmt = select(self.model_class).where(self._soft_delete_filter())

          for col_name, value in filters.items():
              col = getattr(self.model_class, col_name)
              base_stmt = base_stmt.where(col == value)

          # Total count — uses a subquery so filters are applied consistently
          count_stmt = select(func.count()).select_from(base_stmt.subquery())
          total: int = (await self.session.execute(count_stmt)).scalar_one()

          # Determine order column
          if order_by_col is None:
              order_by_col = getattr(self.model_class, "created_at", self.model_class.id)

          ordered = base_stmt.order_by(
              order_by_col.desc() if order_desc else order_by_col.asc()
          )
          paginated = ordered.offset(params.offset).limit(params.size)
          items = list((await self.session.execute(paginated)).scalars().all())

          return items, total

      # ── Write ──

      async def create(self, data: dict[str, Any]) -> ModelT:
          """
          Insert a new record. Flushes but does NOT commit.
          The service layer owns the transaction boundary (Unit of Work).
          Returns the created instance with all DB-generated fields (id, created_at) populated.
          """
          obj = self.model_class(**data)
          self.session.add(obj)
          await self.session.flush()
          await self.session.refresh(obj)
          return obj

      async def update(self, id: IDT, data: dict[str, Any]) -> ModelT:
          """
          Update fields on an existing non-deleted record. Flushes but does NOT commit.
          Raises NotFoundError if not found or soft-deleted.
          """
          obj = await self.get_by_id_or_raise(id)
          for key, value in data.items():
              setattr(obj, key, value)
          await self.session.flush()
          await self.session.refresh(obj)
          return obj

      async def soft_delete(self, id: IDT) -> None:
          """
          Sets deleted_at = now() on the record. Flushes but does NOT commit.
          Raises NotFoundError if not found or already deleted.
          Raises AttributeError if model does not have SoftDeleteMixin.
          """
          if not hasattr(self.model_class, "deleted_at"):
              raise AttributeError(
                  f"{self.model_class.__name__} does not support soft delete (no deleted_at column)"
              )
          obj = await self.get_by_id_or_raise(id)
          obj.deleted_at = datetime.utcnow()
          await self.session.flush()

─── RULES ───
- All write methods flush but NEVER commit. The service layer calls session.commit().
  This is the Unit of Work pattern — the repo is inside the transaction, not the owner of it.
- list_paginated accepts only equality filters via dict — never raw SQL strings.
  This is the Specification Pattern: filters are data, not code.
- _soft_delete_filter() must handle models without deleted_at gracefully.
- model_class resolution must work for concrete subclass declarations.
- get_by_id_or_raise imports NotFoundError from src.core.exceptions.

─── VALIDATION ───
Run:
  python -c "
import asyncio, uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.base_repository import BaseRepository
from src.auth.models import User
from src.destinations.models import Destination

class UserRepo(BaseRepository[User, uuid.UUID]):
    pass

class DestRepo(BaseRepository[Destination, uuid.UUID]):
    pass

mock = AsyncMock(spec=AsyncSession)
ur = UserRepo(mock)
dr = DestRepo(mock)

# Verify model_class resolution
assert ur.model_class is User, f'Expected User, got {ur.model_class}'
assert dr.model_class is Destination, f'Expected Destination, got {dr.model_class}'

# Verify soft delete filter — User has deleted_at, Destination does not
from sqlalchemy import true
u_filter = ur._soft_delete_filter()
d_filter = dr._soft_delete_filter()
print('User soft delete filter:', u_filter)
print('Destination filter (should be true()):', d_filter)
assert 'deleted_at' in str(u_filter), 'User filter should reference deleted_at'

print('PASS — BaseRepository resolves model_class and soft-delete correctly')
"

Expected: PASS, correct filter printed for each repo type.
```

---

## Step 1.6 — core/security/jwt.py + permissions.py

```
Read AGENT.md before proceeding.

TASK: Implement JWT creation/verification and the two FastAPI auth dependencies.
This is step 1.6. Install python-jose now.

─── INSTALL ───
Append to requirements.txt:
  python-jose[cryptography]==3.3.0  # JWT — step 1.6

Install:
  pip install "python-jose[cryptography]==3.3.0"

─── IMPLEMENT src/core/security/jwt.py ───

  import uuid
  from dataclasses import dataclass
  from datetime import datetime, timedelta, timezone
  from jose import jwt, JWTError, ExpiredSignatureError
  from src.config import get_settings

  ALGORITHM = "HS256"
  ACCESS_TOKEN_EXPIRE_DAYS = 7

  @dataclass
  class TokenPayload:
      user_id: uuid.UUID
      email: str
      exp: datetime


  def create_access_token(user_id: uuid.UUID, email: str) -> str:
      """
      Create a signed HS256 JWT. Expiry: 7 days from now.
      Claims: sub (user_id as str), email, exp.
      """
      expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
      payload = {
          "sub": str(user_id),
          "email": email,
          "exp": expire,
      }
      return jwt.encode(payload, get_settings().SECRET_KEY, algorithm=ALGORITHM)


  def verify_token(token: str) -> TokenPayload | None:
      """
      Decode and validate a JWT. Returns TokenPayload on success, None on any failure.
      NEVER raises — all exceptions are caught and return None.
      Blueprint rule: Expired token → 401 (via caller checking None). Never 422 or 500.
      """
      try:
          payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[ALGORITHM])
          sub = payload.get("sub")
          email = payload.get("email")
          exp_raw = payload.get("exp")
          if not sub or not email or not exp_raw:
              return None
          return TokenPayload(
              user_id=uuid.UUID(sub),
              email=email,
              exp=datetime.fromtimestamp(exp_raw, tz=timezone.utc),
          )
      except (JWTError, ExpiredSignatureError, ValueError, KeyError, Exception):
          return None

─── IMPLEMENT src/core/security/permissions.py ───

  from fastapi import Request, Depends, Header
  from fastapi.security import OAuth2PasswordBearer
  from src.core.security.jwt import verify_token, TokenPayload
  from src.core.exceptions import UnauthorizedError

  # auto_error=False — we handle the 401 ourselves via WandrError, not FastAPI's default
  oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


  async def require_auth(
      token: str | None = Depends(oauth2_scheme),
  ) -> TokenPayload:
      """
      FastAPI dependency for protected endpoints.
      Raises UnauthorizedError (401) if token missing or invalid.
      """
      if not token:
          raise UnauthorizedError("Authentication required")
      payload = verify_token(token)
      if payload is None:
          raise UnauthorizedError("Invalid or expired token")
      return payload


  async def optional_auth(
      authorization: str | None = Header(default=None),
  ) -> TokenPayload | None:
      """
      FastAPI dependency for endpoints that work for both guests and authenticated users.
      Returns TokenPayload for authenticated users, None for guests.
      Never raises — guest access is valid.
      """
      if not authorization or not authorization.startswith("Bearer "):
          return None
      token = authorization.removeprefix("Bearer ").strip()
      return verify_token(token)


  async def get_current_user_id(
      payload: TokenPayload = Depends(require_auth),
  ) -> "uuid.UUID":
      """Convenience dependency — returns just the user_id UUID."""
      import uuid
      return payload.user_id

─── RULES ───
- verify_token NEVER raises. Every exception path returns None.
  Callers check the None return and decide what to do (raise or allow guest).
- require_auth raises UnauthorizedError (our WandrError subclass), never HTTPException.
  The global exception handler in main.py converts it to a 401 JSON response.
- optional_auth returns None for guests — anonymous trip planning is a core feature.
- Tokens use timezone-aware datetimes (timezone.utc). Never datetime.utcnow() (deprecated in 3.12).

─── VALIDATION ───
Run:
  python -c "
import uuid
from src.core.security.jwt import create_access_token, verify_token
from datetime import datetime, timedelta, timezone

uid = uuid.uuid4()
token = create_access_token(uid, 'test@wandr.dev')
print('Token length:', len(token))

# Valid token
p = verify_token(token)
assert p is not None, 'valid token returned None'
assert p.user_id == uid, f'user_id mismatch: {p.user_id} != {uid}'
assert p.email == 'test@wandr.dev'
print('Valid token payload:', p.user_id, p.email)

# Bad token — must return None, not raise
assert verify_token('not.a.token') is None
assert verify_token('') is None
assert verify_token('a.b.c') is None
print('Invalid tokens all returned None')

# Expired token — must return None
from jose import jwt as jose_jwt
from src.config import get_settings
expired = jose_jwt.encode(
    {'sub': str(uid), 'email': 'x@x.com', 'exp': datetime.now(timezone.utc) - timedelta(hours=1)},
    get_settings().SECRET_KEY, algorithm='HS256'
)
assert verify_token(expired) is None
print('Expired token returned None')
print('PASS')
"

Expected: PASS, all assertions pass. No exceptions raised.
```

---

## Step 1.7a — auth/schemas.py + auth/exceptions.py

```
Read AGENT.md before proceeding.

TASK: Implement all auth Pydantic schemas and auth-specific exceptions.
This is step 1.7a — schemas and exceptions only. No HTTP or DB logic yet.
No package installs.

─── IMPLEMENT src/auth/schemas.py ───

  import uuid
  from datetime import datetime
  from pydantic import BaseModel, EmailStr, ConfigDict


  class UserOut(BaseModel):
      """Public representation of a User. Used in all auth responses."""
      model_config = ConfigDict(from_attributes=True)

      id: uuid.UUID
      email: str
      name: str
      avatar_url: str | None
      is_active: bool
      created_at: datetime


  class AuthMeResponse(BaseModel):
      """
      Response for GET /auth/me — works for both guests and authenticated users.
      Guests: is_guest=True, user=None, session_id set.
      Authenticated: is_guest=False, user=UserOut, session_id set.
      """
      is_guest: bool
      session_id: str
      user: UserOut | None = None


  class TokenResponse(BaseModel):
      """Returned after successful OAuth callback."""
      access_token: str
      token_type: str = "bearer"
      user: UserOut


  class GoogleCallbackParams(BaseModel):
      """Query params received from Google on OAuth callback."""
      code: str
      state: str | None = None
      error: str | None = None

─── IMPLEMENT src/auth/exceptions.py ───

Auth-specific exceptions. All inherit from WandrError via existing subclasses.

  from src.core.exceptions import UnauthorizedError, ExternalServiceError


  class GoogleOAuthError(ExternalServiceError):
      """Raised when Google OAuth token exchange or userinfo call fails."""
      def __init__(self, message: str, details: dict | None = None):
          super().__init__(service="google_oauth", message=message, details=details)


  class InvalidTokenError(UnauthorizedError):
      """Raised when a token is present but fails verification."""
      def __init__(self, message: str = "Invalid or expired token"):
          super().__init__(message=message)


  class AccountInactiveError(UnauthorizedError):
      """Raised when a valid token belongs to a deactivated user."""
      def __init__(self):
          super().__init__(message="Account is deactivated")

─── RULES ───
- UserOut must have model_config = ConfigDict(from_attributes=True) so SQLAlchemy
  model instances can be passed directly to UserOut(**user.__dict__) or UserOut.model_validate(user).
- Schemas have NO imports from auth/models.py or auth/repository.py — schemas are pure Pydantic.
- Exceptions inherit from WandrError subclasses only — never from HTTPException.

─── VALIDATION ───
Run:
  python -c "
from src.auth.schemas import UserOut, AuthMeResponse, TokenResponse
from src.auth.exceptions import GoogleOAuthError, InvalidTokenError, AccountInactiveError
import uuid
from datetime import datetime

# Guest response
r = AuthMeResponse(is_guest=True, session_id='test-session-123')
assert r.user is None
assert r.is_guest is True
print('Guest response:', r.model_dump())

# Exception hierarchy
e = GoogleOAuthError('timeout')
assert e.status_code == 502
assert e.details['service'] == 'google_oauth'

e2 = InvalidTokenError()
assert e2.status_code == 401

print('PASS')
"

Expected: PASS, guest response printed.
```

---

## Step 1.7b — auth/repository.py + auth/service.py

```
Read AGENT.md before proceeding.

TASK: Implement the auth repository and service. Pure DB + business logic — no HTTP.
This is step 1.7b. Install httpx now (used for Google OAuth calls).

─── INSTALL ───
Append to requirements.txt:
  httpx==0.27.0   # async HTTP client — step 1.7b (used for OAuth, Nominatim, OSRM)

Install:
  pip install httpx==0.27.0

─── IMPLEMENT src/auth/repository.py ───

  import uuid
  from sqlalchemy import select
  from sqlalchemy.ext.asyncio import AsyncSession
  from src.core.database.base_repository import BaseRepository
  from src.auth.models import User


  class UserRepository(BaseRepository[User, uuid.UUID]):

      async def get_by_email(self, email: str) -> User | None:
          stmt = select(User).where(
              User.email == email,
              User.deleted_at.is_(None),
          )
          return (await self.session.execute(stmt)).scalar_one_or_none()

      async def get_by_google_id(self, google_id: str) -> User | None:
          stmt = select(User).where(
              User.google_id == google_id,
              User.deleted_at.is_(None),
          )
          return (await self.session.execute(stmt)).scalar_one_or_none()

─── IMPLEMENT src/auth/service.py ───

  import uuid
  import httpx
  import structlog
  from sqlalchemy.ext.asyncio import AsyncSession

  from src.auth.models import User
  from src.auth.repository import UserRepository
  from src.auth.exceptions import GoogleOAuthError
  from src.core.exceptions import UnauthorizedError

  log = structlog.get_logger()

  GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
  GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


  class AuthService:

      def __init__(self, session: AsyncSession) -> None:
          self.session = session
          self.repo = UserRepository(session)

      async def upsert_google_user(
          self,
          google_id: str,
          email: str,
          name: str,
          avatar_url: str | None,
      ) -> User:
          """
          Find user by google_id → fall back to email lookup → create if not found.
          Update avatar_url and google_id if they changed.
          Commits the transaction — auth upsert is always a standalone operation.
          """
          user = await self.repo.get_by_google_id(google_id)
          if user is None:
              user = await self.repo.get_by_email(email)

          if user is None:
              user = await self.repo.create({
                  "google_id": google_id,
                  "email": email,
                  "name": name,
                  "avatar_url": avatar_url,
                  "is_active": True,
              })
              log.info("auth.user_created", email=email)
          else:
              updates: dict = {}
              if user.google_id != google_id:
                  updates["google_id"] = google_id
              if user.avatar_url != avatar_url:
                  updates["avatar_url"] = avatar_url
              if updates:
                  await self.repo.update(user.id, updates)
                  log.info("auth.user_updated", user_id=str(user.id), fields=list(updates.keys()))

          await self.session.commit()
          await self.session.refresh(user)
          return user

      async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
          return await self.repo.get_by_id(user_id)

      async def verify_google_token(self, access_token: str) -> dict:
          """
          Verify a Google access token via Google's userinfo endpoint.
          Returns the userinfo dict on success.
          Raises GoogleOAuthError on network failure.
          Raises UnauthorizedError if Google rejects the token.
          Timeout: 10s.
          """
          try:
              async with httpx.AsyncClient(timeout=10.0) as client:
                  response = await client.get(
                      GOOGLE_USERINFO_URL,
                      headers={"Authorization": f"Bearer {access_token}"},
                  )
                  if response.status_code in (400, 401):
                      raise UnauthorizedError("Google rejected the access token")
                  response.raise_for_status()
                  return response.json()
          except UnauthorizedError:
              raise
          except httpx.TimeoutException:
              raise GoogleOAuthError("Google OAuth userinfo request timed out")
          except httpx.HTTPStatusError as e:
              raise GoogleOAuthError(
                  f"Google OAuth returned {e.response.status_code}",
                  details={"status": e.response.status_code},
              )
          except httpx.RequestError as e:
              raise GoogleOAuthError(f"Google OAuth connection error: {type(e).__name__}")

      async def exchange_code_for_token(
          self,
          code: str,
          redirect_uri: str,
          client_id: str,
          client_secret: str,
      ) -> str:
          """
          Exchange an OAuth authorization code for a Google access token.
          Returns the access_token string.
          Raises GoogleOAuthError on any failure.
          """
          try:
              async with httpx.AsyncClient(timeout=10.0) as client:
                  response = await client.post(
                      GOOGLE_TOKEN_URL,
                      data={
                          "code": code,
                          "client_id": client_id,
                          "client_secret": client_secret,
                          "redirect_uri": redirect_uri,
                          "grant_type": "authorization_code",
                      },
                  )
                  response.raise_for_status()
                  data = response.json()
                  access_token = data.get("access_token")
                  if not access_token:
                      raise GoogleOAuthError("No access_token in Google token response")
                  return access_token
          except GoogleOAuthError:
              raise
          except httpx.TimeoutException:
              raise GoogleOAuthError("Google token exchange timed out")
          except httpx.HTTPStatusError as e:
              raise GoogleOAuthError(f"Google token exchange failed: {e.response.status_code}")
          except httpx.RequestError as e:
              raise GoogleOAuthError(f"Google token exchange connection error: {type(e).__name__}")

─── RULES ───
- Router calls Service only. Service calls Repository only. This file has NO FastAPI imports.
- upsert_google_user commits — exception to the "service flushes, caller commits" rule because
  auth upsert is always a standalone operation, never part of a larger transaction.
- All Google HTTP calls have explicit 10.0s timeouts. No unbounded httpx calls.
- verify_google_token and exchange_code_for_token raise only WandrError subclasses — never raw
  httpx exceptions or HTTPException.

─── VALIDATION ───
Run:
  python -c "
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.repository import UserRepository
from src.auth.service import AuthService
import uuid

mock_session = AsyncMock(spec=AsyncSession)
repo = UserRepository(mock_session)
svc = AuthService(mock_session)
assert repo.model_class.__name__ == 'User'
print('Repository model_class:', repo.model_class.__name__)
print('Service instantiated OK')
print('PASS')
"

Expected: PASS, no import errors.
```

---

## Step 1.7c — auth/router.py + Register in main.py

```
Read AGENT.md before proceeding.

TASK: Implement the auth router with all four endpoints and register it in main.py.
This is step 1.7c. No package installs.

─── ADD TO src/config.py ───
Add these three optional settings to the Settings class (empty defaults — OAuth is opt-in):
  GOOGLE_CLIENT_ID: str = ""
  GOOGLE_CLIENT_SECRET: str = ""
  GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"

─── IMPLEMENT src/auth/router.py ───
Router prefix="/api/v1/auth", tags=["auth"].

Four endpoints:

1. GET /api/v1/auth/google — Start OAuth flow
   - If GOOGLE_CLIENT_ID is empty: return ApiResponse(data={"message": "Google OAuth not configured"})
   - Otherwise: build Google OAuth URL with scopes "openid email profile" and
     redirect to it via RedirectResponse.
   - Google OAuth URL: https://accounts.google.com/o/oauth2/v2/auth
   - Required params: client_id, redirect_uri, response_type=code, scope, access_type=offline

2. GET /api/v1/auth/callback — Handle OAuth redirect from Google
   - Receives code: str and optional error: str as query params.
   - If error param present: redirect to "/auth/error?reason={error}"
   - Call AuthService.exchange_code_for_token(code, redirect_uri, client_id, client_secret)
   - Call AuthService.verify_google_token(access_token) → userinfo dict
   - Call AuthService.upsert_google_user(google_id, email, name, avatar_url)
   - Create JWT: create_access_token(user.id, user.email)
   - Set httpOnly cookie "wandr_token":
       response.set_cookie(
           "wandr_token", token,
           httponly=True, samesite="lax",
           secure=(settings.ENVIRONMENT == "production"),
           max_age=7 * 24 * 3600,
       )
   - Return ApiResponse[TokenResponse]
   - Wrap entire handler in try/except WandrError — on auth errors, return ErrorResponse
     with appropriate status code rather than raising (OAuth errors shouldn't be 500s).

3. GET /api/v1/auth/me — Current user or guest info
   - Dependency: optional_auth → TokenPayload | None
   - Also reads cookie "wandr_session" for guest session ID.
   - If authenticated (payload not None):
       user = await AuthService(db).get_user_by_id(payload.user_id)
       if user is None: raise UnauthorizedError("User account not found")
       return ApiResponse(data=AuthMeResponse(is_guest=False, session_id=str(user.id), user=UserOut.model_validate(user)))
   - If guest:
       session_id = request.cookies.get("wandr_session") or str(uuid.uuid4())
       response.set_cookie("wandr_session", session_id, httponly=False, samesite="lax", max_age=30*24*3600)
       return ApiResponse(data=AuthMeResponse(is_guest=True, session_id=session_id, user=None))

4. POST /api/v1/auth/logout — Clear auth cookies
   - Delete "wandr_token" cookie: response.delete_cookie("wandr_token")
   - No auth required — gracefully handles already-logged-out state.
   - Return ApiResponse(data={"message": "Logged out"})

Dependencies injected:
  db: AsyncSession = Depends(get_db)
  settings: Settings = Depends(get_settings)  (or call get_settings() directly)

─── UPDATE src/main.py ───
Register the auth router in create_app():
  from src.auth.router import router as auth_router
  app.include_router(auth_router)

Add a comment above all include_router calls:
  # ── Routers — registered here as phases complete ──

─── RULES ───
- This router calls AuthService only. Never calls UserRepository directly.
- All WandrError exceptions propagate to the global exception handler in main.py — do NOT
  add try/except for WandrError in individual route handlers (exception: the OAuth callback,
  where a domain error should not produce a 500 HTML page).
- optional_auth returns None for guests — this is valid, not an error.
- Cookie secure=True only in production. Dev uses HTTP localhost where secure=True breaks cookies.

─── VALIDATION ───
Start server:
  uvicorn src.main:app --reload

Test guest me endpoint:
  curl -s http://localhost:8000/api/v1/auth/me | python -m json.tool

Expected:
  {
    "success": true,
    "data": {
      "is_guest": true,
      "session_id": "<uuid>",
      "user": null
    },
    "message": null
  }

Test logout (no auth required):
  curl -s -X POST http://localhost:8000/api/v1/auth/logout | python -m json.tool

Expected:
  {"success": true, "data": {"message": "Logged out"}, "message": null}

Test Google start (OAuth not configured in dev):
  curl -s http://localhost:8000/api/v1/auth/google | python -m json.tool

Expected: ApiResponse with "Google OAuth not configured" message (or redirect if keys are set).
```

---

## Step 1.8 — core/middleware/logging.py — Request ID + Latency Middleware

```
Read AGENT.md before proceeding.

TASK: Implement the request logging middleware that attaches X-Request-ID and logs latency
for every request. This is step 1.8. No package installs.

─── IMPLEMENT src/core/middleware/logging.py ───

  import time
  import uuid
  import structlog
  from starlette.middleware.base import BaseHTTPMiddleware
  from starlette.requests import Request
  from starlette.responses import Response


  class RequestLoggingMiddleware(BaseHTTPMiddleware):
      """
      Chain-of-Responsibility link: outermost middleware layer.
      Responsibilities:
        1. Generate or propagate X-Request-ID
        2. Bind request context to structlog so all log lines in this request share request_id
        3. Log request.start and request.end with latency_ms
        4. Add X-Request-ID to response headers
      """

      async def dispatch(self, request: Request, call_next) -> Response:
          # 1. Generate or preserve request ID
          request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

          # 2. Bind to structlog context for this request — flows into every log line
          structlog.contextvars.clear_contextvars()
          structlog.contextvars.bind_contextvars(
              request_id=request_id,
              method=request.method,
              path=request.url.path,
          )

          log = structlog.get_logger()
          start = time.perf_counter()
          log.info("request.start")

          # 3. Process request — re-raise exceptions after logging (never swallow)
          try:
              response = await call_next(request)
          except Exception as exc:
              elapsed_ms = int((time.perf_counter() - start) * 1000)
              log.error("request.error", latency_ms=elapsed_ms, error=str(exc), exc_info=True)
              raise

          # 4. Log completion
          elapsed_ms = int((time.perf_counter() - start) * 1000)
          log.info("request.end", status_code=response.status_code, latency_ms=elapsed_ms)

          # 5. Add request ID to response headers
          response.headers["X-Request-ID"] = request_id
          return response

─── UPDATE src/main.py ───
In create_app(), register the middleware.
Middleware wraps in LIFO order in Starlette — add_middleware calls stack up.
RequestLoggingMiddleware should be outermost (first to receive the request).
In Starlette, "outermost" means it's added LAST with add_middleware.

Add after the app is created but before include_router calls:
  from src.core.middleware.logging import RequestLoggingMiddleware
  app.add_middleware(RequestLoggingMiddleware)

─── RULES ───
- structlog.contextvars.clear_contextvars() at the start of every request is mandatory.
  Without it, context from a previous request on the same worker leaks into the current one.
  This is especially dangerous in async where workers handle many requests.
- X-Request-ID from incoming headers is preserved — supports distributed tracing where a
  gateway (nginx, Cloudflare) sets the ID upstream.
- latency_ms is measured with time.perf_counter() — not datetime — for sub-ms resolution.
- The middleware must re-raise all exceptions. It logs and passes through. Never swallows.
- Do NOT log request or response bodies — PII risk.

─── VALIDATION ───
Start server (if not already running):
  uvicorn src.main:app --reload

Test 1 — X-Request-ID appears in response:
  curl -si http://localhost:8000/api/v1/health | grep -i "x-request-id"

Expected: line like:  x-request-id: <some-uuid>

Test 2 — Custom request ID is preserved:
  curl -si -H "X-Request-ID: my-trace-id-42" http://localhost:8000/api/v1/health | grep -i "x-request-id"

Expected: x-request-id: my-trace-id-42

Test 3 — Check server log output shows both log lines with the same request_id:
  # Look at the uvicorn terminal — you should see:
  # request.start  request_id=<uuid> method=GET path=/api/v1/health
  # request.end    request_id=<uuid> status_code=200 latency_ms=<N>
  # Both lines must have the SAME request_id.
```

---

## Step 1.9 — Migration 003: TripEditEvent

```
Read AGENT.md before proceeding.

TASK: Add the TripEditEvent model to trips/models.py and run migration 003.
This is step 1.9. No package installs.

─── ADD TO src/trips/models.py ───
Add EditType enum and TripEditEvent class at the bottom of the existing file.

  import enum as _enum  # use alias to avoid shadowing existing imports

  class EditType(str, _enum.Enum):
      REORDER        = "reorder"
      REMOVE_STOP    = "remove_stop"
      ADD_STOP       = "add_stop"
      REOPTIMIZE_DAY = "reoptimize_day"


  class TripEditEvent(Base, UUIDMixin, TimestampMixin):
      """
      Append-only audit record for every user-initiated trip edit.
      Used by evaluation.service.record_edit() to flag user_edited=True
      on the linked TripEvaluation. Never soft-deleted.
      """
      __tablename__ = "trip_edit_events"

      trip_id: Mapped[uuid.UUID] = mapped_column(
          PgUUID(as_uuid=True),
          ForeignKey("trips.id", ondelete="CASCADE"),
          nullable=False,
          index=True,
      )
      edit_type: Mapped[EditType] = mapped_column(
          SAEnum(EditType, name="edit_type"),
          nullable=False,
      )
      day_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
      place_id: Mapped[uuid.UUID | None] = mapped_column(
          PgUUID(as_uuid=True),
          ForeignKey("places.id", ondelete="SET NULL"),
          nullable=True,
      )
      payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

      __table_args__ = (
          Index("ix_trip_edit_events_trip_created", "trip_id", "created_at"),
      )

      def __repr__(self) -> str:
          return f"<TripEditEvent id={self.id} trip={self.trip_id} type={self.edit_type}>"

─── UPDATE alembic/env.py ───
Update the trips import line to include TripEditEvent:
  from src.trips.models import Trip, TripPlace, TripStatus, TripEditEvent  # noqa: F401

─── GENERATE AND RUN MIGRATION 003 ───
Generate:
  alembic revision --autogenerate -m "add_trip_edit_events"

Review the generated file:
  [ ] trip_edit_events table present
  [ ] edit_type enum created
  [ ] ForeignKey to trips.id (CASCADE) and places.id (SET NULL)
  [ ] Index on (trip_id, created_at)
  [ ] Should NOT touch any existing tables

Run:
  alembic upgrade head

─── VALIDATION ───
  docker exec wandr_postgres psql -U wandr -d wandr -c "\dt"

Expected: 7 tables — the previous 6 plus trip_edit_events.

  docker exec wandr_postgres psql -U wandr -d wandr -c "\d trip_edit_events"

Expected: all columns listed — id, trip_id, edit_type, day_number, place_id, payload, created_at, updated_at.

  docker exec wandr_postgres psql -U wandr -d wandr -c "SELECT typname FROM pg_type WHERE typname = 'edit_type';"

Expected: one row with typname = edit_type.
```

---

## Step 1.10 — core/middleware/rate_limit.py ★ NEW

```
Read AGENT.md before proceeding.

TASK: Implement the rate limit middleware with an in-memory backend for dev.
Blueprint (step 6.4): rate limiter on /planner/generate, 10 req/min per IP, returns 429 + Retry-After.
Building it now (not P6) because the middleware chain is assembled here.
This is step 1.10. No package installs.

─── IMPLEMENT src/core/middleware/rate_limit.py ───

  import time
  import asyncio
  import structlog
  from collections import defaultdict
  from starlette.middleware.base import BaseHTTPMiddleware
  from starlette.requests import Request
  from starlette.responses import Response, JSONResponse
  from src.core.responses import ErrorResponse

  log = structlog.get_logger()

  # Default: 60 requests per 60 seconds
  DEFAULT_LIMIT = 60
  DEFAULT_WINDOW = 60

  # Per-route overrides: path_prefix → (limit, window_seconds)
  ROUTE_LIMITS: dict[str, tuple[int, int]] = {
      "/api/v1/planner/generate": (10, 60),  # expensive — 10/min
  }


  class InMemoryRateLimiter:
      """
      Sliding window rate limiter backed by in-memory dict.
      Safe for single-process async use. NOT shared across workers.
      For multi-worker prod: replace with RedisRateLimiter (P6 concern via REDIS_URL).
      """

      def __init__(self) -> None:
          self._windows: dict[str, list[float]] = defaultdict(list)
          self._lock = asyncio.Lock()

      async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
          """
          Returns (allowed, remaining_requests).
          Sliding window: only counts requests within the last `window` seconds.
          """
          async with self._lock:
              now = time.monotonic()
              cutoff = now - window
              self._windows[key] = [t for t in self._windows[key] if t > cutoff]
              count = len(self._windows[key])
              if count >= limit:
                  return False, 0
              self._windows[key].append(now)
              return True, limit - count - 1


  _limiter = InMemoryRateLimiter()


  class RateLimitMiddleware(BaseHTTPMiddleware):

      async def dispatch(self, request: Request, call_next) -> Response:
          # Client identity: X-Forwarded-For (behind proxy) or direct client host
          forwarded = request.headers.get("X-Forwarded-For", "")
          client_ip = forwarded.split(",")[0].strip() or (
              request.client.host if request.client else "unknown"
          )

          # Route-specific limit lookup
          path = request.url.path
          limit, window = DEFAULT_LIMIT, DEFAULT_WINDOW
          for prefix, (rl, rw) in ROUTE_LIMITS.items():
              if path.startswith(prefix):
                  limit, window = rl, rw
                  break

          key = f"{client_ip}:{path}"

          try:
              allowed, remaining = await _limiter.is_allowed(key, limit, window)
          except Exception as exc:
              # Rate limiter failure MUST fail open — never block a user because of a limiter bug
              log.warning("rate_limiter.error", error=str(exc))
              allowed, remaining = True, -1

          if not allowed:
              return JSONResponse(
                  status_code=429,
                  headers={
                      "Retry-After": str(window),
                      "X-RateLimit-Limit": str(limit),
                      "X-RateLimit-Remaining": "0",
                  },
                  content=ErrorResponse(
                      code="rate_limit_exceeded",
                      message=f"Too many requests. Retry after {window} seconds.",
                  ).model_dump(),
              )

          response = await call_next(request)
          response.headers["X-RateLimit-Limit"] = str(limit)
          if remaining >= 0:
              response.headers["X-RateLimit-Remaining"] = str(remaining)
          return response

─── UPDATE src/main.py ───
Register RateLimitMiddleware AFTER RequestLoggingMiddleware in create_app():
  from src.core.middleware.rate_limit import RateLimitMiddleware
  app.add_middleware(RateLimitMiddleware)
  app.add_middleware(RequestLoggingMiddleware)

Note on order: Starlette wraps in LIFO. add_middleware(RateLimitMiddleware) then
add_middleware(RequestLoggingMiddleware) means RequestLoggingMiddleware is outermost
(receives request first). Adjust the order to match this.

─── RULES ───
- Rate limiter errors MUST fail open (allow the request) — never let a limiter bug block users.
- Retry-After header is required by RFC 6585 when returning 429.
- The in-memory limiter is NOT shared across workers. Acceptable for dev and single-worker prod.
  Multi-worker prod uses Redis — that's a P6 concern (REDIS_URL env var).

─── VALIDATION ───
Start server and check rate limit headers appear on health endpoint:
  curl -si http://localhost:8000/api/v1/health | grep -i "x-ratelimit"

Expected:
  x-ratelimit-limit: 60
  x-ratelimit-remaining: 59

Verify planner route has tighter limit:
  python -c "
from src.core.middleware.rate_limit import ROUTE_LIMITS
assert '/api/v1/planner/generate' in ROUTE_LIMITS
limit, window = ROUTE_LIMITS['/api/v1/planner/generate']
assert limit == 10, f'Expected 10, got {limit}'
assert window == 60
print('Planner route limit:', limit, 'per', window, 'seconds')
print('PASS')
"
```

---

## Step 1.11 — pytest Harness + conftest.py + First Tests ★ NEW

```
Read AGENT.md before proceeding.

TASK: Install pytest, implement the test conftest, and write the first integration tests.
The test harness must exist before P2 adds more domain code.
This is step 1.11.

─── INSTALL ───
Append to requirements.txt:
  pytest==8.2.2              # test runner — step 1.11
  pytest-asyncio==0.23.7    # async test support — step 1.11
  pytest-mock==3.14.0       # mock fixtures — step 1.11

Install:
  pip install pytest==8.2.2 pytest-asyncio==0.23.7 pytest-mock==3.14.0

─── CREATE pytest.ini at repo root ───

  [pytest]
  asyncio_mode = auto
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  filterwarnings =
      ignore::DeprecationWarning
      ignore::PendingDeprecationWarning

─── IMPLEMENT tests/conftest.py ───

  import uuid
  import pytest
  from typing import AsyncGenerator
  from httpx import AsyncClient, ASGITransport
  from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
  from src.main import create_app
  from src.core.database.base import Base
  from src.core.database.session import get_db
  from src.config import get_settings


  def _test_db_url() -> str:
      """Derive test DB URL by appending _test to the dev DB name."""
      url = get_settings().DATABASE_URL
      # Replace last path segment: /wandr → /wandr_test
      parts = url.rsplit("/", 1)
      return parts[0] + "/" + parts[1].split("?")[0] + "_test"


  @pytest.fixture(scope="session")
  async def test_engine():
      """Session-scoped engine. Creates all tables once, drops them after the session."""
      engine = create_async_engine(_test_db_url(), echo=False)
      async with engine.begin() as conn:
          # Ensure PostGIS is available in test DB
          await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS postgis"))
          await conn.run_sync(Base.metadata.create_all)
      yield engine
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.drop_all)
      await engine.dispose()


  @pytest.fixture
  async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
      """
      Function-scoped session that rolls back after each test.
      This ensures tests are isolated and order-independent.
      """
      factory = async_sessionmaker(test_engine, expire_on_commit=False)
      async with factory() as session:
          async with session.begin():
              yield session
              await session.rollback()


  @pytest.fixture
  async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
      """
      Async HTTP test client with the DB session overridden to use the test session.
      """
      app = create_app()

      async def _override_get_db():
          yield db_session

      app.dependency_overrides[get_db] = _override_get_db

      async with AsyncClient(
          transport=ASGITransport(app=app),
          base_url="http://test",
      ) as ac:
          yield ac

      app.dependency_overrides.clear()


  @pytest.fixture
  def auth_token() -> str:
      """Returns a valid JWT for a synthetic test user."""
      from src.core.security.jwt import create_access_token
      return create_access_token(uuid.uuid4(), "testuser@wandr.dev")


  @pytest.fixture
  def auth_headers(auth_token) -> dict:
      """Authorization headers for authenticated test requests."""
      return {"Authorization": f"Bearer {auth_token}"}

─── CREATE tests/auth/test_auth_router.py ───

  import pytest


  async def test_health(client):
      r = await client.get("/api/v1/health")
      assert r.status_code == 200
      data = r.json()
      assert data["success"] is True
      assert data["data"]["status"] == "ok"


  async def test_auth_me_guest(client):
      r = await client.get("/api/v1/auth/me")
      assert r.status_code == 200
      data = r.json()
      assert data["success"] is True
      assert data["data"]["is_guest"] is True
      assert data["data"]["user"] is None
      assert data["data"]["session_id"]  # non-empty


  async def test_auth_logout_no_auth(client):
      r = await client.post("/api/v1/auth/logout")
      assert r.status_code == 200
      assert r.json()["success"] is True


  async def test_require_auth_rejects_no_token(client):
      """Verify require_auth dependency returns 401 for missing token."""
      # Use the health endpoint (no auth) as baseline, then test a protected route.
      # Since no protected routes exist yet, test the JWT verification directly.
      from src.core.security.jwt import verify_token
      assert verify_token("invalid.token.here") is None


  async def test_x_request_id_present(client):
      r = await client.get("/api/v1/health")
      assert "x-request-id" in r.headers


  async def test_rate_limit_headers_present(client):
      r = await client.get("/api/v1/health")
      assert "x-ratelimit-limit" in r.headers
      assert "x-ratelimit-remaining" in r.headers

─── PRE-STEP: Create test database ───
  docker exec wandr_postgres psql -U wandr -c "CREATE DATABASE wandr_test;"

─── VALIDATION ───
  pytest tests/ -v

Expected:
  tests/auth/test_auth_router.py::test_health PASSED
  tests/auth/test_auth_router.py::test_auth_me_guest PASSED
  tests/auth/test_auth_router.py::test_auth_logout_no_auth PASSED
  tests/auth/test_auth_router.py::test_require_auth_rejects_no_token PASSED
  tests/auth/test_auth_router.py::test_x_request_id_present PASSED
  tests/auth/test_auth_router.py::test_rate_limit_headers_present PASSED
  6 passed in <N>s

Zero failures. Fix any failure before step 1.12.
```

---

## Step 1.12 — P1 Database Smoke Test Script ★ NEW

```
Read AGENT.md before proceeding.

TASK: Write and run a comprehensive DB smoke test script that validates the entire P1
data layer end-to-end — connection, all 7 tables, PostGIS geometry, soft-delete, and
migration state. This catches issues that unit tests miss.
This is step 1.12. Install shapely now (needed for PostGIS geometry construction).

─── INSTALL ───
Append to requirements.txt:
  shapely==2.0.5   # geometry construction for PostGIS seed/test scripts — step 1.12

Install:
  pip install shapely==2.0.5

─── CREATE scripts/test_p1_smoke.py ───

  """
  P1 database smoke test — run against the dev database after completing all P1 steps.
  Not a pytest test. Run directly: python scripts/test_p1_smoke.py
  All DB writes are rolled back at the end. No permanent data is written.
  """
  import asyncio
  import uuid
  from datetime import datetime
  from sqlalchemy import text, select
  from sqlalchemy.ext.asyncio import AsyncSession
  from geoalchemy2.shape import from_shape
  from shapely.geometry import Point

  from src.core.database.session import get_engine, AsyncSessionLocal
  from src.auth.models import User
  from src.destinations.models import Destination
  from src.places.models import Place
  from src.trips.models import Trip, TripPlace, TripStatus, TripEditEvent, EditType
  from src.evaluation.models import TripEvaluation

  EXPECTED_TABLES = [
      "users", "destinations", "places",
      "trips", "trip_places", "trip_evaluations", "trip_edit_events",
  ]


  def _ok(msg: str) -> None:
      print(f"  ✓ {msg}")


  def _fail(msg: str) -> None:
      print(f"  ✗ {msg}")
      raise AssertionError(msg)


  async def test_connection() -> None:
      print("\n─── 1. Connection + Pool ───")
      engine = get_engine()
      async with engine.connect() as conn:
          ver = (await conn.execute(text("SELECT version()"))).scalar()
          _ok(f"Connected: {ver[:55]}...")
          db = (await conn.execute(text("SELECT current_database()"))).scalar()
          _ok(f"Database: {db}")


  async def test_all_tables_exist() -> None:
      print("\n─── 2. All 7 Tables Exist ───")
      engine = get_engine()
      async with engine.connect() as conn:
          for table in EXPECTED_TABLES:
              exists = (await conn.execute(
                  text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='{table}')")
              )).scalar()
              if exists:
                  _ok(table)
              else:
                  _fail(f"Table '{table}' missing — run: alembic upgrade head")


  async def test_postgis_geometry() -> None:
      print("\n─── 3. PostGIS Geometry Insert + Read ───")
      async with AsyncSessionLocal() as session:
          # Insert a destination first (Place has FK to destinations)
          dest = Destination(
              name="Smoke Test City",
              country="Testland",
              display_name="Smoke Test City, Testland",
              lat=27.041,
              lng=88.263,
          )
          session.add(dest)
          await session.flush()
          _ok(f"Destination inserted: id={dest.id}")

          # Insert a Place with a PostGIS POINT geometry
          place = Place(
              osm_id=f"smoke_{uuid.uuid4().hex[:12]}",
              name="Tiger Hill (Smoke Test)",
              category="viewpoint",
              destination_id=dest.id,
              location=from_shape(Point(88.263, 27.041), srid=4326),
          )
          session.add(place)
          await session.flush()
          _ok(f"Place with PostGIS geometry inserted: id={place.id}")

          # Read back and verify
          fetched = (await session.execute(select(Place).where(Place.id == place.id))).scalar_one()
          assert fetched.name == "Tiger Hill (Smoke Test)"
          _ok(f"Place read back: name={fetched.name}, category={fetched.category}")

          # Spatial query — ST_DWithin radius check
          nearby = (await session.execute(
              text(
                  "SELECT COUNT(*) FROM places "
                  "WHERE ST_DWithin(location::geography, ST_MakePoint(:lng, :lat)::geography, :radius)"
              ),
              {"lng": 88.263, "lat": 27.041, "radius": 1000},
          )).scalar()
          assert nearby >= 1
          _ok(f"ST_DWithin radius query returned {nearby} result(s)")

          await session.rollback()
          _ok("Rolled back — no permanent data written")


  async def test_soft_delete_filter() -> None:
      print("\n─── 4. Soft Delete Filter ───")
      async with AsyncSessionLocal() as session:
          user = User(
              email=f"smoke_{uuid.uuid4().hex[:8]}@wandr.dev",
              name="Smoke Test User",
              is_active=True,
          )
          session.add(user)
          await session.flush()
          uid = user.id

          # Soft-delete
          user.deleted_at = datetime.utcnow()
          await session.flush()

          # Raw query should still find it
          raw = (await session.execute(select(User).where(User.id == uid))).scalar_one_or_none()
          assert raw is not None, "Raw query should find soft-deleted user"

          # Filtered query should not find it
          filtered = (await session.execute(
              select(User).where(User.id == uid, User.deleted_at.is_(None))
          )).scalar_one_or_none()
          assert filtered is None, "Filtered query must NOT return soft-deleted user"

          _ok("Soft delete filter works correctly")
          await session.rollback()


  async def test_migration_state() -> None:
      print("\n─── 5. Migration State ───")
      engine = get_engine()
      async with engine.connect() as conn:
          rev = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
          assert rev is not None, "No migrations applied — run: alembic upgrade head"
          _ok(f"Current alembic revision: {rev}")


  async def main() -> None:
      print("=" * 52)
      print("  Wandr P1 — Database Smoke Test")
      print("=" * 52)
      try:
          await test_connection()
          await test_all_tables_exist()
          await test_postgis_geometry()
          await test_soft_delete_filter()
          await test_migration_state()

          print("\n" + "=" * 52)
          print("  ALL P1 SMOKE TESTS PASSED ✓")
          print("  Ready to start P2.")
          print("=" * 52 + "\n")
      except AssertionError as e:
          print(f"\n✗ SMOKE TEST FAILED: {e}")
          raise SystemExit(1)
      except Exception as e:
          print(f"\n✗ UNEXPECTED ERROR: {type(e).__name__}: {e}")
          import traceback; traceback.print_exc()
          raise SystemExit(1)


  if __name__ == "__main__":
      asyncio.run(main())

─── VALIDATION ───
Run:
  python scripts/test_p1_smoke.py

Expected output:
  ====================================================
    Wandr P1 — Database Smoke Test
  ====================================================

  ─── 1. Connection + Pool ───
    ✓ Connected: PostgreSQL 16.x ...
    ✓ Database: wandr

  ─── 2. All 7 Tables Exist ───
    ✓ users
    ✓ destinations
    ✓ places
    ✓ trips
    ✓ trip_places
    ✓ trip_evaluations
    ✓ trip_edit_events

  ─── 3. PostGIS Geometry Insert + Read ───
    ✓ Destination inserted
    ✓ Place with PostGIS geometry inserted
    ✓ Place read back: name=Tiger Hill (Smoke Test), category=viewpoint
    ✓ ST_DWithin radius query returned 1 result(s)
    ✓ Rolled back — no permanent data written

  ─── 4. Soft Delete Filter ───
    ✓ Soft delete filter works correctly

  ─── 5. Migration State ───
    ✓ Current alembic revision: <rev_id>

  ====================================================
    ALL P1 SMOKE TESTS PASSED ✓
    Ready to start P2.
  ====================================================

Do NOT proceed to P2 if any test fails.
```

---

## P1 Complete — Full Verification Checklist

Run this entire block before starting P2. Every item must pass.

```bash
# ── Packages ──
pip show sqlalchemy asyncpg alembic geoalchemy2 python-jose httpx pytest pytest-asyncio shapely | grep "^Name:"
# Expected: all 9 names listed

# ── Database ──
docker compose ps
# Expected: wandr_postgres healthy, wandr_qdrant running

alembic current
# Expected: shows revision with "(head)" label

docker exec wandr_postgres psql -U wandr -d wandr -c "\dt"
# Expected: 7 tables — users, destinations, places, trips, trip_places, trip_evaluations, trip_edit_events

docker exec wandr_postgres psql -U wandr -d wandr -c "\dx"
# Expected: postgis, postgis_topology, uuid-ossp listed

# ── Models import cleanly ──
python -c "
from src.auth.models import User
from src.destinations.models import Destination
from src.places.models import Place
from src.trips.models import Trip, TripPlace, TripStatus, TripEditEvent, EditType
from src.evaluation.models import TripEvaluation
print('All models import OK')
"

# ── BaseRepository ──
python -c "
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database.base_repository import BaseRepository
from src.auth.models import User
class R(BaseRepository[User, uuid.UUID]): pass
r = R(AsyncMock(spec=AsyncSession))
assert r.model_class is User
print('BaseRepository OK')
"

# ── JWT ──
python -c "
import uuid
from src.core.security.jwt import create_access_token, verify_token
uid = uuid.uuid4()
t = create_access_token(uid, 'check@wandr.dev')
p = verify_token(t)
assert p.user_id == uid
assert verify_token('garbage') is None
print('JWT OK')
"

# ── Server starts ──
uvicorn src.main:app --port 8001 &
sleep 3
curl -s http://localhost:8001/api/v1/health | python -m json.tool
kill %1 2>/dev/null
# Expected: {"success": true, "data": {"status": "ok", ...}}

# ── Middleware headers ──
curl -si http://localhost:8000/api/v1/health | grep -i "x-request-id"
# Expected: x-request-id: <uuid>
curl -si http://localhost:8000/api/v1/health | grep -i "x-ratelimit-limit"
# Expected: x-ratelimit-limit: 60

# ── Auth me guest ──
curl -s http://localhost:8000/api/v1/auth/me | python -m json.tool
# Expected: is_guest: true, session_id present, user: null

# ── Pytest suite ──
pytest tests/ -v
# Expected: 6 passed, 0 failed

# ── DB smoke test ──
python scripts/test_p1_smoke.py
# Expected: ALL P1 SMOKE TESTS PASSED ✓

# ── Import guards ──
grep -r "import litellm" src/ --include="*.py" | grep -v "core/llm/client.py"
# Expected: zero results

echo "P1 COMPLETE — proceed to P2"
```
