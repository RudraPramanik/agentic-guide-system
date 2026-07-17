# Wandr — Spec-Driven Development Playbook

> **Audience:** Human developers using Cursor + OpenSpec on this repo.  
> **Not for:** Pasting verbatim into agents as a system prompt — use `openspec/config.yaml` and `docs/context.md` for that.

This guide explains how we build features end-to-end: **think → plan → architect → implement**, using OpenSpec as the execution layer on top of existing Wandr docs.

---

## 1. The layered model (what lives where)

| Layer | Location | Purpose | Who maintains |
|-------|----------|---------|---------------|
| **Checkpoint** | `docs/context.md` | What's done, what's stub, next step | Developer / agent after each validated step |
| **Guardrails** | `AGENT.md` | Non-negotiable coding rules | Team |
| **North star** | `docs/blueprint_final.md` | Full product + phase plan | Team (rare changes) |
| **Architecture** | `docs/app/system.md`, `docs/app/lld.md` | System context + patterns | Team |
| **Build prompts** | `docs/steps/step*.md` | Detailed step instructions + validation | Team (per phase) |
| **Active change** | `openspec/changes/<id>/` | This slice: proposal, spec, design, tasks | OpenSpec + you |
| **Permanent specs** | `openspec/specs/` | Behavior deltas after archive | Grows automatically per shipped change |
| **AI injection** | `openspec/config.yaml` | Project context for OpenSpec artifacts | Team |

**Rule:** Do not copy the whole blueprint into OpenSpec. Specs grow **delta-first** — one slice at a time.

---

## 2. End-to-end workflow

```text
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│  THINKING   │ →  │  PLANNING   │ →  │ ARCHITECTURE │ →  │ IMPLEMENTATION │
│  (explore)  │    │  (propose)  │    │ (artifacts)  │    │    (apply)     │
└─────────────┘    └─────────────┘    └──────────────┘    └────────────────┘
      │                  │                    │                     │
  Optional           Required             Auto-generated         Short prompt
  /opsx:explore      /opsx:propose        proposal.md            /opsx:apply
                                          spec.md
                                          design.md
                                          tasks.md
                                                                    │
                                                              validate →
                                                         update context.md →
                                                           /opsx:archive
```

### Phase 1 — Thinking (optional)

**When:** Scope is fuzzy, tradeoffs matter, or you're new to an area of the codebase.

**Goal:** Understand the problem and options **before** creating artifacts or code.

**Cursor prompt:**
```text
/opsx:explore

I'm about to work on step 1.3 (Alembic + PostGIS).
Read docs/steps/step1.md Step 1.3, docs/context.md, and alembic/env.py.
Summarize risks, file touch list, and whether the blueprint approach still fits.
Do not write code.
```

**Output:** Conversation only. No change folder, no code.

---

### Phase 2 — Planning (required per slice)

**When:** You know *what* slice you're building (e.g. step 1.3, 1.4a, or a feature like "guest checkout").

**Goal:** Create one OpenSpec **change** with scoped artifacts grounded in `docs/steps/` or blueprint.

**Cursor prompt:**
```text
/opsx:propose step-1-3-alembic-postgis

Ground in docs/steps/step1.md Step 1.3 and docs/context.md.
Scope: Step 1.3 only — no models, no step 1.4+.
Put exact validation commands from step1.md into tasks.md.
In proposal.md: non-goals, open questions, and any better alternatives.
Final task in tasks.md: update docs/context.md after validation passes.
Do not implement yet.
```

**You review before apply:**
- `tasks.md` — has checkboxes + proof commands
- `proposal.md` — scope is one slice only
- `spec.md` — behavior delta, not full blueprint copy
- `design.md` — files to touch, patterns from `lld.md`

---

### Phase 3 — Architecture (inside the change)

**When:** During `/opsx:propose` — you don't write this manually unless iterating.

**What's in each artifact:**

| File | Architecture role |
|------|-------------------|
| `proposal.md` | Why, what changes, impact, non-goals, open questions |
| `spec.md` | Testable behavior (Given/When/Then), acceptance criteria |
| `design.md` | How: modules, files, patterns, constraints from AGENT.md |
| `tasks.md` | Ordered implementation checklist with validation gates |

**If design is wrong after review:** edit artifacts directly, or use `/opsx:update` on the change before apply.

---

### Phase 4 — Implementation

**When:** `tasks.md` looks correct.

**Cursor prompt (short — this is the daily default):**
```text
/opsx:apply step-1-3-alembic-postgis
```

The agent reads the change artifacts automatically. You do **not** paste the whole `step1.md` block again.

**After apply:**
1. Run validation commands from `tasks.md`
2. Confirm `docs/context.md` was updated (or update it yourself)
3. Archive:

```text
/opsx:archive step-1-3-alembic-postgis
```

---

## 3. One slice = two prompts (developer cheat sheet)

| Step | You type | When |
|------|----------|------|
| Start slice | `/opsx:propose <change-id>` + grounding line | Once per sub-step |
| Review | Open `openspec/changes/<id>/tasks.md` | Before apply |
| Build | `/opsx:apply <change-id>` | After review |
| Validate | Run terminal commands from `tasks.md` | After apply |
| Finish | `/opsx:archive <change-id>` | After validation passes |

**Grounding line template** (append to every propose):
```text
Ground in docs/steps/step1.md Step <X>.
Scope: Step <X> only — do not implement later steps.
Put validation commands in tasks.md.
Final task: update docs/context.md.
Do not implement yet.
```

---

## 4. Wandr sub-step execution examples

We split large blueprint steps into sub-steps in `docs/steps/step1.md`. Each sub-step gets its **own OpenSpec change**.

### Example A — Step 1.3 (Alembic + PostGIS)

**Propose:**
```text
/opsx:propose step-1-3-alembic-postgis

Ground in docs/steps/step1.md Step 1.3 and docs/context.md.
Scope: alembic.ini, alembic/env.py, alembic/versions/001_enable_postgis.py,
requirements.txt only. No domain models. Model imports in env.py stay empty.
Put `alembic upgrade head` and `\dx` validation in tasks.md.
Final task: update docs/context.md (next step → 1.4a).
Do not implement yet.
```

**Apply:**
```text
/opsx:apply step-1-3-alembic-postgis
```

**Archive:**
```text
/opsx:archive step-1-3-alembic-postgis
```

---

### Example B — Step 1.4a (User + Destination models)

**Propose:**
```text
/opsx:propose step-1-4a-user-destination-models

Ground in docs/steps/step1.md Step 1.4a and docs/context.md.
Assume step 1.3 is archived. Read openspec/specs/ for database conventions.
Scope: User and Destination models only — no Place/Trip models yet.
Update alembic/env.py model imports for new models.py files.
Include step validation block in tasks.md.
Final task: update docs/context.md.
Do not implement yet.
```

**Apply:**
```text
/opsx:apply step-1-4a-user-destination-models
```

---

### Example C — Step 1.4b (Place + Trip + TripPlace models)

**Propose:**
```text
/opsx:propose step-1-4b-place-trip-models

Ground in docs/steps/step1.md Step 1.4b.
Assume 1.4a is done. Reference openspec/specs/ for existing User/Destination models.
Scope: Place, Trip, TripPlace only — no migration 002 yet (that's 1.4d).
Do not implement yet.
```

**Apply:**
```text
/opsx:apply step-1-4b-place-trip-models
```

---

### Example D — New feature (not a numbered step)

For ad-hoc work outside `step*.md`:

**Explore first:**
```text
/opsx:explore

We need rate limiting on public API endpoints. Read AGENT.md, main.py middleware
chain, and docs/app/lld.md. Compare in-memory vs Redis for our MVP. No code yet.
```

**Propose:**
```text
/opsx:propose add-rate-limit-middleware-stub

Ground in docs/blueprint_final.md P1 step 1.10 and AGENT.md.
Scope: middleware stub only — fail open on errors. No Redis yet.
Include pytest or smoke validation in tasks.md.
Do not implement yet.
```

**Apply:**
```text
/opsx:apply add-rate-limit-middleware-stub
```

---

## 5. What tracks automatically vs manually

| Tracks automatically | You do manually |
|---------------------|-----------------|
| Active change folder (`openspec/changes/<id>/`) | Choose change name and scope in propose |
| Task checkboxes in `tasks.md` | Review `tasks.md` before apply |
| `openspec/specs/` after archive | Run validation commands in terminal |
| OpenSpec reads artifacts on `/opsx:apply` | `/opsx:archive` when slice is done |
| `openspec/config.yaml` injects project rules | Keep `docs/context.md` accurate |

**`docs/context.md` is the session checkpoint** — always update it when a build step completes, even if it's the last task in `tasks.md`.

---

## 6. Designing the next phase (e.g. step2 after step1)

When P1 is complete:

```text
/opsx:explore

P1 is archived. Read openspec/specs/, docs/context.md, and blueprint P2 section.
Propose how docs/steps/step2.md should be structured (2.1–2.8).
Flag gaps between blueprint assumptions and what P1 actually shipped.
No code yet.
```

Then propose a planning change (not implementation):

```text
/opsx:propose p2-geo-foundation-plan

Ground in docs/blueprint_final.md P2 and openspec/specs/ from P1.
Output: outline for docs/steps/step2.md with sub-step splits and validation gates.
Do not implement geo code yet.
```

Use archived specs + real code as ground truth; blueprint stays the north star.

---

## 7. Terminal commands (developer reference)

```bash
# Health check
openspec doctor
openspec list                  # active changes
openspec list --specs          # archived domain specs

# Refresh Cursor slash commands after OpenSpec upgrade
openspec update

# Inspect a change
openspec show <change-id>
openspec status --change <change-id>
```

---

## 8. Anti-patterns (do not do these)

| Anti-pattern | Why it's bad |
|--------------|--------------|
| `mkdir openspec/changes/foo` by hand | Bypasses OpenSpec metadata; use `/opsx:propose` |
| Create `specs.md` instead of `spec.md` | Wrong artifact name for `spec-driven` schema |
| Copy whole blueprint into OpenSpec | Stale, untrusted, wastes context |
| One giant change for all of P1 | Hard to validate, review, and archive |
| Paste full `step1.md` block on every apply | Duplicates `tasks.md`; use short `/opsx:apply` |
| Skip archive | `openspec/specs/` never grows; P2 design lacks ground truth |
| Implement without validation | Breaks the step-gated build model |

---

## 9. Quick start (your next session)

1. Read `docs/context.md` → confirm next step (currently **1.3**)
2. Run propose prompt for step 1.3 (Example A above)
3. Review `openspec/changes/step-1-3-alembic-postgis/tasks.md`
4. Run `/opsx:apply step-1-3-alembic-postgis`
5. Validate → archive → confirm `context.md` shows **1.4a** next

---

## Related docs

- `docs/context.md` — current build state
- `docs/steps/step1.md` — P1 detailed prompts + validation
- `docs/blueprint_final.md` — full phase plan
- `docs/app/system.md` · `docs/app/lld.md` — architecture reference
- `AGENT.md` — coding guardrails
- `openspec/config.yaml` — OpenSpec project context (for AI artifacts)
