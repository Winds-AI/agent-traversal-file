---
name: iatf
description: Work with .iatf files for efficient AI agent navigation. Use when creating, editing, validating, or querying structured documents.
---

# IATF - Indexed Agent Traversal Format

Self-indexing document format. Documents have an auto-generated INDEX (~5% of file) and CONTENT (source of truth). Agents read INDEX first, then fetch specific sections by ID — saving 80-95% tokens.

## Commands

```bash
iatf index <file>                # Show INDEX (read this first)
iatf read <file> <id>            # Read section by ID
iatf read <file> --title "Name"  # Read section by title
iatf graph <file>                # Outgoing references (section -> targets)
iatf graph <file> --show-incoming  # Incoming references (impact analysis)
iatf rebuild <file>              # Rebuild INDEX from CONTENT
iatf rebuild-all [dir]           # Rebuild all .iatf files
iatf validate <file>             # Check structure and references
iatf watch <file>                # Auto-rebuild on save
iatf watch-dir <dir>             # Watch all .iatf files in directory
```

## File Structure

```
:::IATF
@title: Document Title
@purpose: Optional purpose

===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
# Section Title {#section-id | lines:15-25 | words:120}
> Summary text
  Created: 2025-01-20 | Modified: 2025-01-29
  Hash: bf5d286

===CONTENT===

{#section-id}
@summary: Brief description for INDEX
# Section Title
Content here. Reference other sections with {@other-id}.
{/section-id}
```

## Rules

- CONTENT is source of truth; INDEX is auto-generated (never edit INDEX manually)
- Line numbers in INDEX are **absolute file positions** — read ranges directly with `sed -n 'start,endp'`
- `{@section-id}` creates cross-references (validated on rebuild; no self-references allowed)
- Max nesting depth: 2 levels
- All content must be inside `{#id}...{/id}` blocks

## Agent Workflow

1. **Discover**: `iatf index file.iatf` — scan summaries for relevant sections
2. **Analyze**: `iatf graph file.iatf` — check dependencies before editing
3. **Load**: `iatf read file.iatf section-id` — fetch only what you need
4. **Edit**: modify CONTENT, then `iatf rebuild file.iatf`

**Fallback without CLI** (use absolute line numbers from INDEX):
```bash
sed -n '42,57p' document.iatf
```
