#!/usr/bin/env bash
# Hosted data-plane backup checklist (no secrets written to repo).
# Usage: ./ops/backup.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

cat <<'EOF'
==> Wandr production backup checklist (hosted data plane)

1. PostGIS (Supabase/Neon/etc.)
   - Enable provider automated backups / PITR in the dashboard.
   - Optional manual: pg_dump from a trusted machine (never commit dumps).

2. Qdrant Cloud
   - Use Qdrant Cloud snapshots / cluster backup if available on your plan.

3. Secrets
   - Store .env.production in a password manager; never git commit.

4. Application image
   - GHCR retains images by SHA; rollback via ops/rollback.sh <sha>.

This script does not dump databases automatically (out of scope for VPS API-only host).
EOF
