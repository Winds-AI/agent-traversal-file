# IATF File Format Example

## Full File Structure

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

## Key Elements

- `:::IATF` — file type marker (first line)
- `@title` / `@purpose` — document metadata
- `===INDEX===` — auto-generated section (never edit manually)
- `===CONTENT===` — source of truth, all editable content lives here
- `{#id}...{/id}` — section delimiters
- `@summary:` — brief description used to generate INDEX entries
- `{@other-id}` — cross-reference to another section
