# IATF Format Specification (Living Draft)

This document defines the current IATF behavior implemented by the CLI.

## 1. Purpose

IATF keeps structured navigation and source content in one file:

- `INDEX`: generated navigation cache
- `CONTENT`: source of truth

Authoring model:

1. Edit `CONTENT`.
2. Rebuild INDEX (`iatf rebuild`).
3. Validate (`iatf validate`).

## 2. File Layout

Required top-level order:

1. Header (must start with `:::IATF`)
2. `===INDEX===` (optional before first rebuild)
3. `===CONTENT===` (required)

Example skeleton:

```text
:::IATF
@title: Document Title
@purpose: Why this file exists

===CONTENT===

{#main}
@summary: Main section summary
# Main
Body
{/main}
```

## 3. Header

### 3.1 Required Marker

First line must be:

```text
:::IATF
```

### 3.2 Metadata

Supported documented fields:
- `@title:`
- `@purpose:`

Implementation note:
- Additional header `@...` fields are currently tolerated by CLI.

## 4. INDEX Section

## 4.1 Delimiter

```text
===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
<!-- Generated: 2026-02-17T10:23:10Z -->
<!-- Content-Hash: sha256:abc1234 -->
```

## 4.2 Entry Syntax (Current Canonical)

Each section entry is ID-first:

```text
- section-id {lines:start-end | words:count}
Section summary line
Created: YYYY-MM-DD | Modified: YYYY-MM-DD
Hash: abc1234
```

Rules:
- Entry header line starts with `- `.
- `section-id` format matches CONTENT section IDs.
- `lines:start-end` are absolute file line numbers (1-indexed).
- `words:count` is computed from section body lines.
- Summary is plain text (no prefix marker).
- `Created`/`Modified` and `Hash` are optional metadata lines produced by rebuild.

## 4.3 Semantics

- INDEX is generated from CONTENT order.
- INDEX stores IDs, ranges, summaries, and timestamps/hashes.
- Consumers should treat INDEX as cache and CONTENT as source of truth.

## 5. CONTENT Section

## 5.1 Delimiter

```text
===CONTENT===
```

## 5.2 Section Blocks

```text
{#section-id}
@summary: Summary used in INDEX
# Optional human heading
Body lines...
{/section-id}
```

Rules:
- Opening and closing tags must match.
- IDs must be unique in document.
- All non-empty content must be inside a section block.
- Nesting is allowed.

### 5.3 Section ID Grammar

ID must:
- start with a letter
- contain letters, numbers, `_`, `-`

Examples:
- valid: `intro`, `release-gates`, `section_2`
- invalid: `1intro`, `my section`

### 5.4 Section Header Annotations

Immediately after `{#id}`:
- only `@summary:` is supported as section-header annotation
- unsupported annotation keys here are validation errors

Inside regular body content, `@...` text is treated as plain text.

## 6. References

Reference syntax:

```text
{@section-id}
```

Validation rules:
- target must exist
- self-reference is invalid
- cycles are allowed

Fenced code behavior:
- references inside fenced code blocks are ignored by reference validation/extraction
- code fence toggle is only lines exactly equal to ````` (trimmed)

## 7. Rebuild Behavior

`iatf rebuild`:

1. Parses CONTENT sections.
2. Validates duplicate IDs and references.
3. Computes per-section word counts and content hash.
4. Updates INDEX entries and metadata.
5. Writes `Generated` and `Content-Hash` comments.

Modification tracking:
- `Created` is initialized when first indexed.
- `Modified` updates when section hash changes.

## 8. Validation Contract

## 8.1 Errors (exit code 1)

- Missing `:::IATF`
- Missing `===CONTENT===`
- Multiple INDEX or CONTENT delimiters
- INDEX appears after CONTENT
- Invalid nesting (unclosed/mismatched tags)
- Content outside section blocks
- Duplicate section IDs
- Unsupported section-header annotation
- Missing-reference / self-reference errors
- When INDEX exists: INDEX/CONTENT mismatch errors
  - missing IDs on either side
  - line-range mismatch
  - duplicate IDs in INDEX

Implementation note:
- nesting depth >2 is currently enforced during INDEX/CONTENT consistency validation (i.e., when INDEX exists).

## 8.2 Warnings (exit code 0)

- Missing INDEX
- Missing/invalid/stale INDEX Content-Hash
- No sections found in CONTENT

## 9. Command Dependencies on INDEX

Require INDEX:
- `iatf index`
- `iatf find`
- `iatf read`
- `iatf read-many`

Do not require INDEX:
- `iatf graph` (reads CONTENT directly)

## 10. Minimal End-to-End Example

Authoring file (before rebuild):

```text
:::IATF
@title: Minimal

===CONTENT===

{#intro}
@summary: Intro summary
# Intro
See {@details}.
{/intro}

{#details}
@summary: Detail summary
# Details
Body text.
{/details}
```

After rebuild (shape):

```text
:::IATF
@title: Minimal

===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
<!-- Generated: 2026-02-17T...Z -->
<!-- Content-Hash: sha256:... -->

- intro {lines:... | words:...}
Intro summary
Created: 2026-02-17 | Modified: 2026-02-17
Hash: ...

- details {lines:... | words:...}
Detail summary
Created: 2026-02-17 | Modified: 2026-02-17
Hash: ...

===CONTENT===
...
```

## 11. Practical Notes

- Use `iatf rebuild` + `iatf validate` as a pair.
- Avoid hand-editing INDEX metadata.
- Prefer ID-based retrieval (`find` -> `read`/`read-many`).
