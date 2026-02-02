# Convert TXT to IATF Format

You are converting a plain text document into IATF (Indexed Agent Traversal Format). IATF is a structured format where AI agents can navigate large documents efficiently by reading only the sections they need.

## Input
- Source document: `{SOURCE_PATH}`
- Output file: `{OUTPUT_PATH}`

## IATF File Structure

```
:::IATF
@title: Document Title

===INDEX===

===CONTENT===

{#section-id}
@summary: One-line description
# Section Title
Content with {@other-section-id} cross-references.
{/section-id}
```

**The INDEX section is auto-generated.** You only write the CONTENT sections.

---

## PHASE 1: Analyze Document

Read the entire source document. Identify all sections by looking for:
- Numbered headings
- Capitalized headers
- Clear topic changes
- Logical groupings

Create a section map in this format:

```
SECTION MAP:
1. [Title] | #[section-id] | Lines [start]-[end]
   Summary: [one line]
   References: [list of section-ids this content mentions or relates to]

2. [Title] | #[section-id] | Lines [start]-[end]
   Summary: [one line]
   References: [...]
```

Section ID rules:
- Lowercase only
- Hyphens for spaces: `admin-user-types` not `Admin User Types`
- No special characters
- Predictable from title

---

## PHASE 2: Spawn Sub-Agents for Content

Divide sections among sub-agents:
- 10+ sections: 2-3 sections per sub-agent
- 5-10 sections: 1-2 sections per sub-agent
- <5 sections: single agent

**Sub-Agent Prompt Template:**

```
Convert these sections from {SOURCE_PATH} to IATF format:

ASSIGNED SECTIONS:
- #[section-id-1]: lines [start]-[end]
- #[section-id-2]: lines [start]-[end]

CROSS-REFERENCE MAP (add {@id} when content mentions these):
- [section-id-1] should reference: [list]
- [section-id-2] should reference: [list]

FOR EACH SECTION, OUTPUT:

{#section-id}
@summary: [One line describing the section for the index]
# [Section Title]
[Content from source, with {@section-id} references added where the text
mentions topics that have their own sections]
{/section-id}

RULES:
1. Preserve all key details: lists, field names, numbers, specifications
2. Add {@section-id} when content mentions another section's topic
3. Remove image placeholder text ("A screenshot of...", "Description automatically generated")
4. Keep the original meaning - do not summarize or omit important details
5. @summary must be ONE line only
```

---

## PHASE 3: Assemble Final Document

Collect all sub-agent outputs and assemble:

```
:::IATF
@title: [Document Title from source]

===INDEX===

===CONTENT===

[All section blocks in logical order from sub-agents]
```

Save to `{OUTPUT_PATH}`.

Then run: `iatf rebuild {OUTPUT_PATH}`

---

## Cross-Reference Guide

Add `{@section-id}` when the text:

| Pattern in Source | Action |
|-------------------|--------|
| Names another module/section | Add `{@that-module}` |
| Says "as mentioned in X" | Add `{@x-section}` |
| Says "see X" or "refer to X" | Add `{@x-section}` |
| Describes a dependency | Reference the dependency |
| Uses a term defined elsewhere | Reference the definition |

**Example:**

Source:
```
The admin portal manages customer bookings, payments, and Bandar credits.
Changes to customer data are logged in the notification system.
```

IATF:
```
The admin portal manages customer bookings {@booking-management}, payments {@payments-management}, and Bandar credits {@bandar-credits-management}.
Changes to customer data are logged in the notification system {@notifications-management}.
```

---

## Validation Before Completion

Verify:
- [ ] File starts with `:::IATF`
- [ ] Every section has `{#id}`, `@summary:`, `# Title`, `{/id}`
- [ ] All `{@references}` point to section IDs that exist in the document
- [ ] No image placeholder text remains
- [ ] Section IDs are lowercase-hyphenated
- [ ] `iatf rebuild` runs without errors

---

## Execute Now

1. Read `{SOURCE_PATH}`
2. Output section map
3. Spawn sub-agents with their assigned sections
4. Assemble outputs into `{OUTPUT_PATH}`
5. Run `iatf rebuild {OUTPUT_PATH}`
