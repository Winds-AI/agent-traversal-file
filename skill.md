---
name: atf
description: Agent Traversable File format for token-efficient document navigation. Use when working with large documentation files to read only relevant sections instead of entire files.
allowed-tools: Bash(atf)
---

# ATF - Agent Traversable File

## Quick start

```bash
atf index <file>                    # Get table of contents with section IDs
atf read <file> <section-id>        # Read specific section by ID
atf read <file> --title "Title"     # Read section by title (case-insensitive)
atf rebuild <file>                  # Regenerate index (for maintainers)
atf validate <file>                 # Check file structure
```

## Core workflow

1. **Index first**: `atf index <file>` to see available sections
2. **Parse section IDs**: Extract from `{#section-id | ...}` format
3. **Read selectively**: `atf read <file> <section-id>` for specific content

## Why use ATF?

**Token efficiency**: Read only the sections you need from large documents instead of loading entire files.

Example: A 5000-line API reference has 50 sections. Instead of reading all 5000 lines, read the 100-line section you need.

## File structure

```
:::ATF/1.0

===INDEX===
# Section Title {#section-id | lines:34-55 | words:71}
> Section summary
  Created: 2025-01-20 | Modified: 2025-01-20

===CONTENT===
{#section-id}
@summary: Section summary
# Section Title
Content here...
{/section-id}
```

## Commands

### Navigation

```bash
atf index <file>                    # List all sections with IDs and line ranges
atf read <file> <section-id>        # Extract section by ID
atf read <file> --title "Query"     # Find section by title (case-insensitive, partial match)
```

### Maintenance

```bash
atf validate <file>                 # Check structure, nesting, index consistency
atf rebuild <file>                  # Regenerate INDEX (auto-updates hashes, timestamps)
atf rebuild-all [dir]               # Rebuild all .atf files
atf watch <file>                    # Auto-rebuild on changes
```

## Examples

**Navigate large documentation:**
```bash
atf index api-reference.atf
# Output:
# # Authentication {#auth | lines:50-120 | words:234}
# # Users API {#users-api | lines:150-250 | words:345}
# # Payments API {#payments-api | lines:252-350 | words:412}

atf read api-reference.atf auth          # Read auth section only
atf read api-reference.atf --title "payment"  # Search by title
```

**Title search (case-insensitive, partial match):**
```bash
atf read docs.atf --title "install"      # Matches "Installation"
atf read docs.atf --title "QUICK"        # Matches "Quick Start"
```

## Editing CONTENT section

When modifying ATF files, **only edit the CONTENT section**, never the INDEX.

**Basic structure:**
```
{#section-id}
@summary: Brief description for the index
@created: YYYY-MM-DD
@modified: YYYY-MM-DD
@hash: abc1234
# Section Title

Your content here...

{/section-id}
```

**Adding a new section:**
1. Add section in CONTENT using `{#id}...{/id}` tags
2. Include `@summary` and `@created` metadata
3. Run `atf rebuild <file>` to regenerate INDEX

**Editing existing section:**
1. Modify content between `{#id}` and `{/id}` tags
2. Don't manually change `@hash` or `@modified` - these auto-update on rebuild
3. Run `atf rebuild <file>` to update INDEX and metadata

**Deleting a section:**
1. Remove entire `{#id}...{/id}` block from CONTENT
2. Run `atf rebuild <file>` to update INDEX

**Rules:**
- Section IDs must be unique
- IDs must start with letter, then letters/numbers/hyphens/underscores
- Maximum 2 levels of nesting
- No content outside `{#id}...{/id}` blocks in CONTENT section
- Always run `atf rebuild` after any CONTENT changes

## Best practices

**DO:**
- Always run `atf index` before reading content
- Use section IDs from the index output
- Use `--title` when you know the topic but not the ID
- Edit only CONTENT section, then rebuild to update INDEX

**DON'T:**
- Don't read entire .atf files with Read tool - use `atf read` instead
- Don't guess section IDs - check the index first
- Don't edit INDEX manually - use `atf rebuild`
- Don't manually update `@hash` or `@modified` - rebuild does this

## Section ID rules

Valid: `intro`, `getting-started`, `api_v2`, `section1`
Invalid: `123start`, `-intro`, `my section`

Must start with letter, then letters/numbers/hyphens/underscores.

## Exit codes

- `0`: Success
- `1`: Not found (file, section, title)
- `2`: Invalid format

## Nesting

ATF supports 2 levels of nesting. Reading a parent section includes all nested children.

```
# Parent {#parent | lines:10-50 | words:100}
## Child {#child | lines:20-40 | words:45}
```
