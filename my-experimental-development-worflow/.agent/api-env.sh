#!/usr/bin/env bash
# Source once: source .agent/api-env.sh

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export API_BASE="http://192.168.3.155:8000/api"
export API_TOKENS_FILE="$DIR/tokens.toml"
export API_MODE="safe-updates"  # read-only | safe-updates | full-access
export PATH="$DIR/bin:$PATH"
