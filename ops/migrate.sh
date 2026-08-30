#!/usr/bin/env bash
# Run Alembic migrations against hosted DATABASE_URL.
# Usage: ./ops/migrate.sh
# Env: WANDR_ENV_FILE (default .env.production), WANDR_IMAGE

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_env_file
IMAGE="$(resolve_image)"

echo "==> migrate: $IMAGE (env: $ENV_FILE)"
docker run --rm --env-file "$ENV_FILE" "$IMAGE" alembic upgrade head
echo "==> migrate: done"
