#!/usr/bin/env bash
# Show docker compose service status for production stack.
# Usage: ./ops/status.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "$SCRIPT_DIR/lib.sh"

require_env_file
compose ps
