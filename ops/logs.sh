#!/usr/bin/env bash
# Tail API and Caddy logs.
# Usage: ./ops/logs.sh [service]
# Default: api caddy (follow mode)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_env_file
SERVICES=("${@:-api caddy}")
compose logs -f --tail=100 "${SERVICES[@]}"
