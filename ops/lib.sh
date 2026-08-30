#!/usr/bin/env bash
# Shared helpers for production ops scripts.
# Env: WANDR_ENV_FILE, COMPOSE_FILE, WANDR_IMAGE, WANDR_GHCR_OWNER, WANDR_API_HOST

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${WANDR_ENV_FILE:-.env.production}"
DEPLOY_CURRENT_TAG_FILE="${DEPLOY_CURRENT_TAG_FILE:-.deploy-current-tag}"
DEPLOY_PREVIOUS_TAG_FILE="${DEPLOY_PREVIOUS_TAG_FILE:-.deploy-previous-tag}"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

require_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "error: missing $ENV_FILE (copy from .env.production.example)" >&2
    exit 1
  fi
}

read_env_var() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi
  local value="${line#*=}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf '%s' "$value"
}

resolve_api_host() {
  if [[ -n "${WANDR_API_HOST:-}" ]]; then
    printf '%s' "$WANDR_API_HOST"
    return
  fi
  read_env_var WANDR_API_HOST
}

resolve_image() {
  if [[ -n "${WANDR_IMAGE:-}" ]]; then
    printf '%s' "$WANDR_IMAGE"
    return
  fi
  printf '%s' "wandr-api:prod"
}

image_from_tag() {
  local tag="$1"
  if [[ -n "${WANDR_IMAGE:-}" ]]; then
    printf '%s' "$WANDR_IMAGE"
    return
  fi
  local owner="${WANDR_GHCR_OWNER:-}"
  if [[ -z "$owner" ]]; then
  owner="$(read_env_var WANDR_GHCR_OWNER 2>/dev/null || true)"
  fi
  if [[ -z "$owner" ]]; then
    echo "error: set WANDR_GHCR_OWNER or export WANDR_IMAGE before deploy with tag" >&2
    exit 1
  fi
  printf 'ghcr.io/%s/wandr-api:%s' "$owner" "$tag"
}
