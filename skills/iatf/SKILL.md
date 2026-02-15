---
name: iatf
description: Work with .iatf files for efficient AI agent navigation. Use when creating, editing, validating, or querying structured documents.
---

# IATF - Indexed Agent Traversal Format

Self-indexing document format. Documents have an auto-generated INDEX (~5% of file) and CONTENT (source of truth). Agents read INDEX first, then fetch specific sections by ID — saving 80-95% tokens.

## Commands

```bash
iatf index <file>                # Show simplified INDEX (titles + summaries)
iatf index <file> --with-dates   # Include INDEX generated date + section Created/Modified
iatf find <file> <query>         # Find ranked section IDs from INDEX summaries/titles
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

See [example-format.md](./example-format.md) for the full file format example.

## Rules

- CONTENT is source of truth; INDEX is auto-generated (never edit INDEX manually)
- Line numbers in INDEX are **absolute file positions** — read ranges directly with `sed -n 'start,endp'`
- `{@section-id}` creates cross-references (validated on rebuild; no self-references allowed)
- Max nesting depth: 2 levels
- All content must be inside `{#id}...{/id}` blocks

## Agent Patterns

```bash
# Filter index for topics
iatf index doc.iatf | grep -i auth

# Find ranked section IDs directly from INDEX
iatf find doc.iatf "credit expiration controversy"

# Read all matching sections
iatf index doc.iatf | grep -oP '#\K[a-z0-9_-]+' | xargs -n1 iatf read doc.iatf

# Extract cross-references from a section
iatf read doc.iatf section-id | grep -oP '\{@\K[^}]+' | sort -u

# Search across multiple files
for f in docs/*.iatf; do iatf index "$f" 2>/dev/null | grep -i topic && echo "^ $f"; done

# Impact analysis: who references this section?
iatf graph doc.iatf --show-incoming | grep "^section-id"

# Query pipeline: find candidate section IDs from index, then read only those sections
DOC="doc.iatf"
iatf index "$DOC" \
  | grep -iE 'credit|banana|expire|expiration|controversy|question' \
  | grep -oP '\{#\K[a-z0-9_-]+' \
  | sort -u \
  | while read -r id; do
      echo "===== $id ====="
      iatf read "$DOC" "$id"
    done

# Targeted section grep (avoid full-file reads)
for id in bandar-credits-management customer-management questions; do
  iatf read "$DOC" "$id" | grep -n -iE 'expire|expiration|controversy|coupon|points'
done

# One-hop expansion via cross-references
seed="bandar-credits-management"
refs=$(iatf read "$DOC" "$seed" | grep -oP '\{@\K[^}]+' | sort -u)
for id in $seed $refs; do
  echo "===== $id ====="
  iatf read "$DOC" "$id"
done

# Reusable helper for section-scoped retrieval
iatf_query () {
  local doc="$1"; shift
  local q="$*"
  iatf index "$doc" \
    | grep -iE "$q" \
    | grep -oP '\{#\K[a-z0-9_-]+' \
    | sort -u \
    | while read -r id; do
        echo "===== $id ====="
        iatf read "$doc" "$id"
      done
}
# usage: iatf_query "$DOC" 'credit|expiration|questions'
```
