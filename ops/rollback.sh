#!/usr/bin/env bash
# Redeploy previous image tag (no Alembic downgrade).
# Usage: ./ops/rollback.sh [previous-tag]
# If omitted, reads .deploy-previous-tag written by deploy.sh.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

TAG="${1:-}"
if [[ -z "$TAG" ]]; then
  if [[ ! -f "$DEPLOY_PREVIOUS_TAG_FILE" ]]; then
    echo "error: no tag argument and missing $DEPLOY_PREVIOUS_TAG_FILE" >&2
    exit 1
  fi
  TAG="$(cat "$DEPLOY_PREVIOUS_TAG_FILE")"
fi

echo "==> rollback: redeploying tag=$TAG"
"$SCRIPT_DIR/deploy.sh" "$TAG"
"$SCRIPT_DIR/health.sh"
