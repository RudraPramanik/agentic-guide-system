#!/usr/bin/env bash
# Pull (if registry image) and restart API + Caddy.
# Usage: ./ops/deploy.sh [git-sha-or-tag]
# Env: WANDR_ENV_FILE, WANDR_IMAGE, WANDR_GHCR_OWNER

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_env_file

TAG="${1:-}"
if [[ -n "$TAG" ]]; then
  export WANDR_IMAGE
  WANDR_IMAGE="$(image_from_tag "$TAG")"
fi

if [[ -f "$DEPLOY_CURRENT_TAG_FILE" ]]; then
  cp "$DEPLOY_CURRENT_TAG_FILE" "$DEPLOY_PREVIOUS_TAG_FILE"
fi
echo "${TAG:-local}" >"$DEPLOY_CURRENT_TAG_FILE"

IMAGE="$(resolve_image)"
echo "==> deploy: image=$IMAGE"

if [[ "$IMAGE" == ghcr.io/* ]]; then
  compose pull api
fi

compose up -d
compose ps
echo "==> deploy: done (stamp: $DEPLOY_CURRENT_TAG_FILE)"
