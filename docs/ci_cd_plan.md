# CI/CD Plan — Wandr Backend

> Companion to `docs/next_version.md` (Blueprint v7.0/v7.1). This file defines the
> CI/CD rollout in two deliberately separated phases: **minimal CI now** (test gate)
> and **full CD later** (auto-deploy), triggered by deploy pain — not by calendar.
>
> Status as of 2026-08-30: **Phase A live** (`.github/workflows/ci.yml` — pytest + docker build).  
> **Phase B-lite in progress** (`.github/workflows/deploy.yml` — GHCR push + SSH `ops/*.sh`; `workflow_dispatch` only).  
> Deployment on VPS: `ops/*.sh` + `docker-compose.prod.yml` + `.env.production` (from `.env.production.example`).

---

## Why CI before the v7 work

Every stage's proof gate in `next_version.md` is *"pytest green."* Six of seven
stages modify files with pinned tests that mock specific client APIs
(`mock_client.search` → `query_points`, `mock_client.upsert` call counts).
Without an automated gate, "tests green" depends on someone remembering to run
them locally — exactly how pinned tests break silently during refactors.

```
                 WITHOUT CI                        WITH CI
                 ──────────                        ────────
P1.Stage 1       "tests green?" — hope so          PR blocked until 3 migrated tests pass
P2.Stage 2       state threading bugs found        evaluation-row assertion runs on
                 days later in prod data             every push
P1.Stage 2       RRF cutover validated by hand     golden harness diff runs automatically;
                 against live Darjeeling data        regression = red build
Rollback         flip env var, pray                revert commit; CI proves dense-only path green
```

---

## Phase A — Minimal CI (NOW, ~half day)

One workflow file: `.github/workflows/ci.yml`. Test gate only — no deploy.

### Jobs

```
┌──────────────────────────────────────────────────────────┐
│  ci.yml                                                  │
│                                                          │
│  job: test                                               │
│    ├─ checkout                                           │
│    ├─ setup-python (match Dockerfile base version)       │
│    ├─ pip install -r requirements.txt -r requirements-   │
│    │   prod.txt (or single lock if consolidated)         │
│    ├─ pytest tests/ -v                                   │
│    └─ (optional, later) ruff / mypy                      │
│                                                          │
│  job: docker-build                                       │
│    ├─ checkout                                           │
│    └─ docker build -f Dockerfile .  (prod image builds)  │
└──────────────────────────────────────────────────────────┘
```

### Triggers

- `push` to `main`
- `pull_request` targeting `main`

### Scope rules

| Do | Don't |
|---|---|
| Run full pytest suite (all suites exist: `tests/search`, `tests/planner`, `tests/core`, `tests/evaluation`) | Deploy anything |
| Build the prod Dockerfile (catches missing deps early — e.g., sentence-transformers exclusion) | Push images to a registry |
| Keep it under ~10 min | Add matrix builds, caching complexity, or coverage thresholds yet |

### Notes

- Tests are fully mocked (Qdrant, LLM, DB via fixtures in `tests/conftest.py`) —
  no services needed in CI. If a test needs Postgres/Qdrant later, add them as
  compose services in the workflow then.
- Secrets: none required for Phase A. LLM_API_KEY etc. stay out of CI entirely.
- Future hook point: when P2.Stage 4 (golden harness) lands, wire
  `scripts/run_evals.py` into this workflow as a third job — one-line addition,
  not a retrofit.

---

## Phase B — Full CD (MUCH LATER, on demand)

**Trigger:** implement only when deploy pain appears — repeated manual
`ops/deploy.sh` mistakes, rollback fumbles, or multi-environment needs.
Do NOT build this preemptively.

### Pipeline shape (when triggered)

```
push main ──▶ CI (Phase A jobs) ──▶ build+push image ──▶ migrate ──▶ deploy ──▶ smoke
                                    │                    │           │          │
                                    registry             alembic    ops/       ops/
                                    (GHCR)               upgrade    deploy.sh  health.sh
                                                         │
                                                         └─ on failure: abort BEFORE deploy
```

### Stages

1. **Image publish** — build prod image, push to registry tagged with git SHA
   (`ghcr.io/<org>/wandr:<sha>`); `latest` never used for deploys.
2. **Migration gate** — run `alembic upgrade head` against staging/prod DB;
   failure aborts pipeline *before* new code ships (old image still runs fine
   against migrated schema per expand-contract discipline).
3. **Deploy** — `ops/deploy.sh <sha>` (existing script becomes the CD executor,
   not a replacement target).
4. **Smoke check** — `ops/health.sh` must pass; failure auto-triggers rollback
   via `ops/rollback.sh`.
5. **Eval gate (post P2.Stage 4)** — optional scheduled/manual golden-harness run
   against a seeded destination; regression blocks release promotion.

### Environment strategy (when needed)

| Env | Purpose | Deploy trigger |
|---|---|---|
| staging | mirror of prod compose; eval runs here | auto on merge to main |
| prod | real users | manual approval (GitHub Environments) after staging green |

### Explicit non-goals for Phase B (until pain demands)

- No blue/green or canary — single-host compose deploy is fine at current scale.
- No infra-as-code (Terraform) — Caddy/nginx configs are static and small.
- No monorepo/frontend pipeline — backend repo only until FE has its own.

---

## Rollout order (ties to next_version.md)

```
NOW          →  Phase A: minimal CI (pytest + docker build)      ← half day
THEN         →  P1.Stage 1  (safe under CI already)
THEN         →  P2.Stages 1→2→3→4  (observability + harness)
THEN         →  P1.Stage 2  (RRF cutover, harness-gated)
LATER        →  P1.Stage 3  (only if evidence demands)
MUCH LATER   →  Phase B: full CD (auto-deploy on every main merge) after VPS secrets verified
```

Rationale: P2.Stage 4 (golden harness) lands *before* P1.Stage 2 (RRF cutover),
so the retrieval change is proven by the harness instead of hoped-for. Phase B-lite
(`deploy.yml`) ships with manual dispatch first; enable push-to-main deploy when
`VPS_*` secrets and `.env.production` on the box are validated.
