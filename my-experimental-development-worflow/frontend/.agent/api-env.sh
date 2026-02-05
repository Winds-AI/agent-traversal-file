#!/usr/bin/env bash
# Source once: source .agent/api-env.sh

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export API_BASE="https://example-backend.com/api"
export API_TOKENS_FILE="$DIR/tokens.toml"
export API_MODE="safe-updates"  # read-only | safe-updates | full-access
export PATH="$DIR/bin:$PATH"
