# Task List

## Task 1: Verify x-hash parsing in Go implementation

**Priority:** High  
**Status:** Pending

### Description
Verify that the Go implementation correctly parses `@x-hash:` annotation from ATF section headers. If parsing is missing, add it and write tests.

### References
- Python implementation: `python/atf.py:82-94` - parses `@x-hash:`
- Go implementation: `go/main.go:182-184` - already parses `@x-hash:`
- Spec: `SPECIFICATION.md:223` - `@x-hash:` reserved annotation
- Implementation gaps: `SPEC_IMPLEMENTATION_INCONSISTENCIES.md:182-192`

### Requirements
1. Verify Go parsing of `@x-hash:` in `parseContentSection()` function
2. Verify Go updates `@x-hash` in `updateContentMetadata()` function
3. Add unit tests for x-hash parsing and update workflow
4. Ensure Python and Go produce identical output for x-hash

### Test Files
- `examples/simple.atf` - contains `@x-hash:` annotations

---

## Task 2: Remove @x- custom prefix documentation

**Priority:** High  
**Status:** Pending

### Description
Remove all documentation mentioning `@x-` prefix for custom metadata tags from all markdown files. The project does not support user-defined tags.

### Files to Update
| File | Line(s) | Content to Remove |
|------|---------|-------------------|
| `SPECIFICATION.md` | 95-99 | "Custom fields are allowed with `@x-` prefix" block |
| `SPECIFICATION.md` | 211 | `@x-custom: Custom metadata` example |
| `SPECIFICATION.md` | 224 | "`@x-*` - Custom metadata (preserved but not processed)" |

### Requirements
1. Remove `@x-` prefix documentation from `SPECIFICATION.md`
2. Keep `@x-hash:` reserved annotation (it's a system tag, not user-defined)
3. Do not modify implementation code (it already ignores unknown tags)

### Related
- Code already ignores user-defined tags: `python/atf.py:82-94` only parses known annotations

---

## Task 3: Add index and read commands for agent-efficient navigation

**Priority:** High  
**Status:** Pending

### Description
Add new CLI commands to enable agents to read only the INDEX section and jump directly to specific sections without parsing the entire file.

### Current Commands (python/atf.py:786-813)
| Command | Purpose |
|---------|---------|----------|
| `rebuild` | Rebuild index for file |
| `rebuild-all` | Rebuild all ATF files |
| `watch` | Auto-rebuild on changes |
| `unwatch` | Stop watching file |
| `validate` | Check file validity |

### Proposed Commands

#### `atf index <file>`
**Purpose:** Output only the INDEX section

**Usage:**
```bash
$ atf index doc.atf
# Output: Lines from ===INDEX=== to ===CONTENT=== (the index only)
```

**Implementation:**
1. Find `===INDEX===` delimiter
2. Find `===CONTENT===` delimiter
3. Output lines between them (exclusive)

**Benefits:** Agent reads ~6 lines instead of entire file (for large docs)

#### `atf read <file> <section-id>`
**Purpose:** Extract content for a specific section by ID

**Usage:**
```bash
$ atf read doc.atf intro
# Output: Lines 22-45 (the {#intro} block content)

$ atf read doc.atf auth-keys
# Output: Lines 50-80 (the {#auth-keys} block)
```

**Implementation:**
1. Read INDEX section
2. Parse line range from `{#section-id | lines:start-end}`
3. Output that specific line range from CONTENT section

#### `atf read <file> --title "Title"`
**Purpose:** Extract content by title match

**Usage:**
```bash
$ atf read doc.atf --title "Introduction"
# Output: Lines for section with title "Introduction"
```

**Implementation:**
1. Read INDEX section
2. Find entry matching title (fuzzy match)
3. Read that section's line range

### Requirements
1. Add `index` command to `python/atf.py` and `go/main.go`
2. Add `read` command with `--id` and `--title` options to both implementations
3. Commands should not modify files (read-only)
4. Output should be clean text (no logging, no progress bars)
5. Exit codes: 0=success, 1=not found, 2=error

### Example Workflow for Agents
```bash
# Phase 1: Agent discovers document structure
$ atf index doc.atf
# Returns: 6 lines (index only)

# Phase 2: Agent finds relevant section
$ atf read doc.atf --title "Authentication"
# Returns: 25 lines (specific section content)

# Phase 3: Agent can now work with section directly
# No need to parse entire file
```

### References
- Current command structure: `python/atf.py:770-823`
- Delimiter-based parsing: `SPECIFICATION.md:59-79`
- Index entry format: `SPECIFICATION.md:121-125`

### Files to Modify
- `python/atf.py` - Add `index` and `read` commands
- `go/main.go` - Add `index` and `read` commands
