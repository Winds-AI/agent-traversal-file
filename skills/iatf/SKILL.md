---
name: iatf
description: Work with .iatf files for efficient AI agent navigation. Use when creating, editing, validating, or querying structured documents.
---

# IATF - Indexed Agent Traversal Format

IATF enables AI agents to navigate large documents efficiently. Instead of loading entire files, agents read the INDEX to find relevant sections, then load only those sections.

## Commands

### Core
```bash
iatf rebuild <file>              # Rebuild INDEX from CONTENT
iatf rebuild-all [dir]           # Rebuild all .iatf files in directory
iatf validate <file>             # Check structure and consistency
iatf index <file>                # Output INDEX section
iatf read <file> <id>            # Read section by ID
iatf read <file> --title "Name"  # Read section by title match
iatf graph <file>                # Show outgoing references (section -> targets)
iatf graph <file> --show-incoming  # Show incoming references (section <- sources)
```

### Watch (Auto-Rebuild)
```bash
iatf watch <file>                # Auto-rebuild on save (silent mode)
iatf watch <file> --debug        # Auto-rebuild with verbose output
iatf watch-dir <dir>             # Watch all .iatf files in directory tree (silent)
iatf watch-dir <dir> --debug     # Watch directory with verbose output
iatf unwatch <file>              # Stop watching
iatf watch --list                # List watched files
```

### Daemon (System-Wide Watching)
```bash
iatf daemon start                # Start daemon (watches paths from ~/.iatf/daemon.json)
iatf daemon start --debug        # Start with verbose logging to ~/.iatf/daemon.log
iatf daemon stop                 # Stop running daemon
iatf daemon status               # Show daemon status and configured paths
iatf daemon install              # Install as OS service (auto-start on boot)
iatf daemon uninstall            # Remove OS service
```

## File Structure

```
:::IATF
@title: Document Title
@purpose: Optional purpose

===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
<!-- Generated: 2025-01-29T10:30:00Z -->
<!-- Content-Hash: sha256:abc123 -->

# Section Title {#section-id | lines:15-25 | words:120}
> Summary from @summary annotation
  Created: 2025-01-20 | Modified: 2025-01-29
  Hash: bf5d286

===CONTENT===

{#section-id}
@summary: Brief description for INDEX
# Section Title

Content here... Reference other sections with {@other-id}.
{/section-id}
```

**Key points:**
- CONTENT is source of truth, INDEX is auto-generated
- Line numbers in INDEX are absolute file positions
- `{@section-id}` creates cross-references (validated on rebuild)
- Sections can nest (parent contains children)
- Max nesting depth: 2 levels

## Watch Features

The tool provides three watch modes:

**Single File (`watch`):**
- 250ms polling with 3-second debounce
- Validates before rebuilding (skips invalid files)
- Silent by default, `--debug` for verbose output
- Perfect for active editing sessions

**Directory (`watch-dir`):**
- Monitors all `.iatf` files in directory tree
- Per-file debouncing (independent timers)
- Auto-detects new files
- Auto-removes deleted files from watch
- Useful for multi-file projects

**Daemon (`daemon`):**
- Background process monitoring multiple paths
- Configured via `~/.iatf/daemon.json`
- Logs to `~/.iatf/daemon.log`
- Install as OS service for auto-start
- Cross-platform (systemd/launchd/schtasks)

**All watch modes validate before rebuilding** - invalid files are skipped (logged in --debug mode).

## Agent Patterns

**Topic discovery:**
```bash
iatf index examples/incident-playbook.iatf | rg -i 'incident|rollback|postmortem'
```

**Dependency check before implementing:**
```bash
iatf graph examples/incident-playbook.iatf | rg '^incident'
```

**Impact analysis before editing:**
```bash
iatf graph examples/incident-playbook.iatf --show-incoming | rg '^postmortem'
```

**Find and read in one step:**
```bash
iatf read examples/incident-playbook.iatf $(iatf index examples/incident-playbook.iatf | rg -i rollback | head -1 | rg -o '#[A-Za-z0-9_-]+' | sed 's/^#//')
```

**Search across files:**
```bash
for f in docs/*.iatf; do iatf index "$f" 2>/dev/null | grep -i payment && echo "^ in $f"; done
```

**Find a topic and open first match:**
```bash
id=$(iatf index examples/incident-playbook.iatf | rg -i rollback | head -1 | rg -o '#[A-Za-z0-9_-]+' | sed 's/^#//')
iatf read examples/incident-playbook.iatf "$id"
```

**Open every matching section:**
```bash
iatf index examples/incident-playbook.iatf | rg -i 'incident|rollback' | rg -o '#[A-Za-z0-9_-]+' | sed 's/^#//' | xargs -n1 iatf read examples/incident-playbook.iatf
```

**Show outgoing references for a section:**
```bash
iatf graph examples/incident-playbook.iatf | rg '^incident'
```

**Show incoming references for a section:**
```bash
iatf graph examples/incident-playbook.iatf --show-incoming | rg '^postmortem'
```

**Extract references mentioned inside a section:**
```bash
iatf read examples/incident-playbook.iatf incident | rg -o '\\{@[A-Za-z0-9_-]+\\}' | tr -d '{@}' | sort -u
```

**Fallback without iatf CLI (read by INDEX line numbers):**
```bash
rg '^# .*\\{#rollback' examples/incident-playbook.iatf
# Example output contains: lines:42-57
sed -n '42,57p' examples/incident-playbook.iatf
```

**Watch while editing (single file):**
```bash
iatf watch examples/incident-playbook.iatf --debug &
# Edit the file, INDEX auto-rebuilds with validation
# Kill with: iatf unwatch examples/incident-playbook.iatf
```

**Watch entire project (multiple files):**
```bash
iatf watch-dir docs --debug &
# All .iatf files auto-rebuild on save
# New files auto-detected
```

**Daemon for continuous monitoring:**
```bash
# Configure watched paths
cat > ~/.iatf/daemon.json <<EOF
{
    "watch_paths": [
        "/home/user/projects",
        "/home/user/docs"
    ]
}
EOF

# Start daemon
iatf daemon start

# Check status
iatf daemon status

# View logs
tail -f ~/.iatf/daemon.log
```

## Command Decision Tree

- **Editing a single file?** -> `iatf watch <file>` for auto-rebuild with debounce
- **Editing multiple files in a directory?** -> `iatf watch-dir <dir>` for per-file monitoring
- **Project-wide continuous watching?** -> `iatf daemon start` (configure `~/.iatf/daemon.json` first)
- **INDEX stale?** -> `iatf rebuild`
- **Check validity?** -> `iatf validate`
- **See structure?** -> `iatf index`
- **Read section?** -> `iatf read <id>`
- **See connections?** -> `iatf graph`

## Templates

**API Documentation:**
```
{#intro}
# Introduction
{/intro}

{#auth}
# Authentication
  {#auth-oauth}
  ## OAuth
  {/auth-oauth}
  {#auth-keys}
  ## API Keys
  {/auth-keys}
{/auth}

{#endpoints}
# Endpoints
  {#endpoints-users}
  ## Users
  {/endpoints-users}
{/endpoints}

{#errors}
# Error Handling
{/errors}
```

**Requirements Document:**
```
{#overview}
# Overview
{/overview}

{#functional}
# Functional Requirements
  {#functional-auth}
  ## Authentication
  {/functional-auth}
  {#functional-api}
  ## API
  {/functional-api}
{/functional}

{#nonfunctional}
# Non-Functional Requirements
  {#nonfunctional-perf}
  ## Performance
  {/nonfunctional-perf}
  {#nonfunctional-security}
  ## Security
  {/nonfunctional-security}
{/nonfunctional}

{#testcases}
# Test Cases
{/testcases}
```

## Performance

Rebuild times (Go implementation):
- 500 lines: ~8ms
- 2,000 lines: ~23ms
- 5,000 lines: ~48ms
- 10,000 lines: ~95ms
