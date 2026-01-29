---
name: iatf
description: Work with .iatf files for efficient AI agent navigation. Use when creating, editing, validating, or querying structured documents.
---

# IATF - Intelligent Agent Traversal Format

IATF enables AI agents to navigate large documents efficiently. Instead of loading entire files, agents read the INDEX to find relevant sections, then load only those sections.

## Commands

```bash
iatf rebuild <file>              # Rebuild INDEX from CONTENT
iatf rebuild-all [dir]           # Rebuild all .iatf files in directory
iatf validate <file>             # Check structure and consistency
iatf index <file>                # Output INDEX section
iatf read <file> <id>            # Read section by ID
iatf read <file> --title "Name"  # Read section by title match
iatf graph <file>                # Show outgoing references (section -> targets)
iatf graph <file> --show-incoming  # Show incoming references (section <- sources)
iatf watch <file>                # Auto-rebuild on save (runs until Ctrl+C)
iatf unwatch <file>              # Stop watching
iatf watch --list                # List watched files
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

## Agent Patterns

**Topic discovery:**
```bash
iatf index project.iatf | grep -i auth
```

**Dependency check before implementing:**
```bash
iatf graph project.iatf | grep "^api-auth ->"
```

**Impact analysis before editing:**
```bash
iatf graph project.iatf --show-incoming | grep "^config <-"
```

**Find and read in one step:**
```bash
iatf read project.iatf $(iatf index project.iatf | grep -i login | head -1 | grep -oP '#\K[a-z0-9_-]+')
```

**Search across files:**
```bash
for f in docs/*.iatf; do iatf index "$f" 2>/dev/null | grep -i payment && echo "^ in $f"; done
```

## Command Decision Tree

- **Editing a file?** → `iatf watch` for auto-rebuild
- **INDEX stale?** → `iatf rebuild`
- **Check validity?** → `iatf validate`
- **See structure?** → `iatf index`
- **Read section?** → `iatf read <id>`
- **See connections?** → `iatf graph`

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
