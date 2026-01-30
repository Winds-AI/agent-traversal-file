#!/usr/bin/env bash
set -euo pipefail

# ===========================================
# CONFIGURATION - EDIT THESE CONSTANTS
# ===========================================
AGENT_API_BASE="https://bandar-app-dev.azurewebsites.net/api"
AGENT_PROJECT="bandar-dev"

# Path to tokens file (gitignored, contains tokens for all projects)
# Format: project-name = "token"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_TOKENS_FILE="${SCRIPT_DIR}/tokens.toml"

# ===========================================
# SECURITY CONFIGURATION
# ===========================================
# Options: "read-only" | "safe-updates" | "full-access"
AGENT_SECURITY_LEVEL="full-access"

# Method allowlists by security level
declare -A SECURITY_METHODS=(
  ["read-only"]="GET"
  ["safe-updates"]="GET POST PUT PATCH"
  ["full-access"]="GET POST PUT PATCH DELETE"
)

# Log file for blocked attempts (empty string to disable)
AGENT_BLOCKED_LOG="${SCRIPT_DIR}/blocked_attempts.log"

# ===========================================
# CORE FUNCTIONS
# ===========================================

get_api_base() {
  echo "${AGENT_API_BASE:-http://localhost:8000}"
}

get_token() {
  local tokens_file="${AGENT_TOKENS_FILE:-${SCRIPT_DIR}/tokens.toml}"
  local project="${AGENT_PROJECT:-}"

  # Check if tokens file exists
  if [[ ! -f "$tokens_file" ]]; then
    echo "ERROR: Tokens file not found: $tokens_file" >&2
    echo "Create it from: cp tokens.example.toml tokens.toml" >&2
    return 1
  fi

  # Check if project is set
  if [[ -z "$project" ]]; then
    echo "ERROR: AGENT_PROJECT not set in configuration" >&2
    return 1
  fi

  # Extract token from TOML (format: project = "token" or project = token)
  local token
  token=$(grep "^${project}[[:space:]]*=" "$tokens_file" 2>/dev/null \
    | sed 's/^[^=]*=[[:space:]]*//; s/^"//; s/"$//')

  if [[ -z "$token" ]]; then
    echo "ERROR: No token found for project '$project' in $tokens_file" >&2
    echo "Add: ${project} = \"your-token\"" >&2
    return 1
  fi

  echo "$token"
}

pretty_print() {
  if command -v jq >/dev/null 2>&1; then
    jq . || cat
  else
    cat
  fi
}

get_allowed_methods() {
  local level="$1"
  if [[ -z "${SECURITY_METHODS[$level]:-}" ]]; then
    echo "ERROR: Unknown security level '$level'" >&2
    return 1
  fi
  echo "${SECURITY_METHODS[$level]}"
}

is_method_allowed() {
  local method="$1"
  local level="${2:-$AGENT_SECURITY_LEVEL}"
  local allowed
  allowed="$(get_allowed_methods "$level")" || return 1
  [[ " $allowed " == *" $method "* ]]
}

log_blocked_attempt() {
  local method="$1" path="$2" level="$3"
  [[ -z "${AGENT_BLOCKED_LOG:-}" ]] && return

  local timestamp allowed
  timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  allowed="$(get_allowed_methods "$level")"
  echo "[$timestamp] BLOCKED | method=$method | path=$path | level=$level | allowed=[${allowed// /,}]" >> "$AGENT_BLOCKED_LOG"
}

print_security_error() {
  local method="$1" path="$2" level="$3"
  local allowed
  allowed="$(get_allowed_methods "$level")"

  cat >&2 <<EOF
================================================================================
SECURITY VIOLATION: Operation not permitted
================================================================================
METHOD:           $method
PATH:             $path
CURRENT LEVEL:    $level
ALLOWED METHODS:  ${allowed// /, }

AVAILABLE SECURITY LEVELS:
  - read-only     : GET only (safest for AI agents)
  - safe-updates  : GET, POST, PUT, PATCH (no DELETE)
  - full-access   : GET, POST, PUT, PATCH, DELETE (use with caution)

TO PROCEED:
  1. Change AGENT_SECURITY_LEVEL in .agent/api.sh to a higher level
  2. Or request human approval for this operation
  3. Or verify the operation is necessary

CONTEXT FOR AI AGENTS:
  This operation requires a higher security level. Consider:
  - Breaking down the operation into smaller, allowed steps
  - Requesting human intervention via your workflow
  - Documenting why this operation is necessary
================================================================================
EOF
}

print_help() {
  cat >&2 <<'EOF'
Usage: api.sh METHOD PATH [options]

METHOD: GET | POST | PUT | PATCH | DELETE
PATH  : e.g., /bandar-admin/discounts

Options:
  -q, --query   key=value        Append query param (repeatable)
               'a=1&b=2'         Append raw query chunk
  -j, --json    JSON_OR_@file    JSON body as string or @file.json
  -F, --form    key=value        Multipart field (repeatable); supports key=@file
  -H, --header  'K: V'           Extra header (repeatable)
      --no-pretty                Disable jq pretty-print
  -h, --help                     Show this help

Notes:
  - Prefer -q over ?a=1&b=2 in PATH to avoid shell quoting issues
  - Use -j for JSON APIs; use -F for multipart; do not mix -j and -F
  - Legacy body as third positional arg is still supported for JSON
EOF
}

require_arg() {
  if [[ $# -lt 2 ]]; then
    echo "Error: $1 requires a value" >&2
    exit 1
  fi
}

build_url() {
  local base="$1" path="$2"
  shift 2
  local -a query_parts=("$@")
  local url="${base%/}${path}"

  if [[ ${#query_parts[@]} -gt 0 ]]; then
    local qs
    qs=$(IFS='&'; echo "${query_parts[*]}")
    if [[ "$path" == *\?* ]]; then
      url="${url}&${qs}"
    else
      url="${url}?${qs}"
    fi
  fi
  echo "$url"
}

execute_curl() {
  local use_pretty="$1"
  shift
  if [[ "$use_pretty" == true ]]; then
    "$@" | pretty_print
  else
    "$@"
  fi
}

# ===========================================
# MAIN
# ===========================================

main() {
  if [[ $# -lt 1 ]]; then
    print_help
    exit 1
  fi

  local method="${1^^}"
  local path="${2:-}"

  if [[ -z "$path" ]]; then
    echo "Error: missing PATH (e.g., /bandar-admin/discounts)" >&2
    print_help
    exit 1
  fi

  shift 2

  # Parse options
  local -a query_parts=() extra_headers=() form_parts=()
  local use_pretty=true json_arg=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -q|--query)  require_arg "$1" "${2:-}"; query_parts+=("$2"); shift 2 ;;
      -j|--json)   require_arg "$1" "${2:-}"; json_arg="$2"; shift 2 ;;
      -F|--form)   require_arg "$1" "${2:-}"; form_parts+=("$2"); shift 2 ;;
      -H|--header) require_arg "$1" "${2:-}"; extra_headers+=("$2"); shift 2 ;;
      --no-pretty) use_pretty=false; shift ;;
      -h|--help)   print_help; exit 0 ;;
      --)          shift; break ;;
      -*)          echo "Unknown option: $1" >&2; print_help; exit 1 ;;
      *)
        # Backward-compat: treat as legacy body if -j/-F not provided yet
        if [[ -z "$json_arg" && ${#form_parts[@]} -eq 0 ]]; then
          json_arg="$1"; shift
        else
          echo "Unexpected argument: $1" >&2; print_help; exit 1
        fi
        ;;
    esac
  done

  # Validate: cannot mix JSON and form
  if [[ -n "$json_arg" && ${#form_parts[@]} -gt 0 ]]; then
    echo "Error: cannot use both JSON (-j) and multipart (-F) in the same request" >&2
    exit 1
  fi

  # Security check
  if ! is_method_allowed "$method" "$AGENT_SECURITY_LEVEL"; then
    print_security_error "$method" "$path" "$AGENT_SECURITY_LEVEL"
    log_blocked_attempt "$method" "$path" "$AGENT_SECURITY_LEVEL"
    exit 1
  fi

  # Build URL
  local url
  url="$(build_url "$(get_api_base)" "$path" "${query_parts[@]+"${query_parts[@]}"}")"

  # Build base curl args
  local -a args=("-sS" "-H" "ngrok-skip-browser-warning: true")
  local token
  token="$(get_token)"
  [[ -n "$token" ]] && args+=("-H" "Authorization: Bearer ${token}")
  for h in "${extra_headers[@]+"${extra_headers[@]}"}"; do
    args+=("-H" "$h")
  done

  # Execute request based on method
  case "$method" in
    GET)
      execute_curl "$use_pretty" curl "${args[@]}" "$url"
      ;;
    DELETE)
      execute_curl "$use_pretty" curl -X DELETE "${args[@]}" "$url"
      ;;
    POST|PUT|PATCH)
      if [[ -z "$json_arg" && ${#form_parts[@]} -eq 0 ]]; then
        echo "Error: missing request body for $method (use -j JSON or -F key=value)" >&2
        exit 1
      fi

      local -a cmd=(curl -X "$method")
      [[ -n "$json_arg" ]] && cmd+=("-H" "Content-Type: application/json" "--data-binary" "$json_arg")
      for f in "${form_parts[@]+"${form_parts[@]}"}"; do
        cmd+=("-F" "$f")
      done
      cmd+=("${args[@]}" "$url")

      execute_curl "$use_pretty" "${cmd[@]}"
      ;;
    *)
      echo "Unsupported method: $method" >&2
      exit 1
      ;;
  esac
}

main "$@"
