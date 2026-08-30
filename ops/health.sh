#!/usr/bin/env bash
# Smoke-check production health endpoint.
# Usage: ./ops/health.sh [https://api.example.com]
# Env: WANDR_API_HOST or WANDR_ENV_FILE

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

BASE_URL="${1:-}"
if [[ -z "$BASE_URL" ]]; then
  require_env_file
  HOST="$(resolve_api_host)"
  BASE_URL="https://${HOST}"
fi
BASE_URL="${BASE_URL%/}"

echo "==> health: GET ${BASE_URL}/api/v1/health"
curl -fsS "${BASE_URL}/api/v1/health"
echo
echo "==> health: ok"
