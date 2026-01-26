# Ideas & Future Directions

This file contains experimental ideas and proposed features. These are not implemented yet and may require significant work. Feel free to pick one and start experimenting!

---

## FUSE/Dokany/macFUSE Filesystem Mounting

**Status:** Idea / Not Started
**Priority:** Low-Medium
**Complexity:** High

### Description

Mount IATF files as virtual filesystems so standard tools (cat, grep, wc, ls) can work directly with sections without needing the `IATF` CLI tool.

### Platforms

| Platform | Library |
|----------|---------|
| Linux | FUSE |
| Windows | Dokany |
| macOS | macFUSE |

### How It Would Work

```bash
# Mount IATF file as filesystem
$ iatf-fuse doc.iatf /mnt/IATF

# Access sections as files/directories
$ ls /mnt/IATF/
index  content/

$ cat /mnt/IATF/index
# Auto-generated index (always current)

$ cat /mnt/IATF/content/intro
# {#intro} section content

$ cat /mnt/IATF/content/auth-keys
# {#auth-keys} section content

# Standard tools work natively
$ grep "TODO" /mnt/IATF/content/*
$ wc -l /mnt/IATF/content/*
```

### Virtual Structure

```
/mnt/IATF/
├── index          # Auto-generated INDEX section (read-only)
├── content/       # Section content as files
│   ├── intro
│   ├── auth-keys
│   ├── endpoints-users
│   └── ...
└── metadata/      # Section metadata
    ├── intro.json
    └── auth-keys.json
```

### Benefits

1. **No rebuild needed** - Filesystem driver always returns current data
2. **Standard tool compatibility** - `grep`, `find`, `wc`, etc. work out of the box
3. **Agent-friendly** - Agents can use normal file operations
4. **Transparent** - User sees filesystem, not IATF format

### Concerns

| Issue | Details |
|-------|---------|
| **Performance** | 20-100x slower than native filesystem (4 context switches per operation) |
| **Security** | Malicious iatf could cause resource exhaustion, path traversal |
| **Complexity** | Requires platform-specific code (FUSE, Dokany, macFUSE) |
| **Cross-platform** | Tests need Linux, Windows, and macOS runners |

### Security Considerations

1. **Resource Limits**
   - Max section count (prevent memory exhaustion)
   - Max section size (prevent huge allocations)
   - Timeout per operation (prevent hangs)

2. **Path Sanitization**
   - Reject paths with `..` (prevent traversal attacks)
   - Restrict to mount point

3. **Input Validation**
   - Validate IATF structure before mounting
   - Reject malformed files

### Implementation Steps

1. Choose FUSE library (Go has `bazil.org/fuse`, Python has `fuse-python`)
2. Implement filesystem driver that:
   - Parses IATF file on mount
   - Exposes sections as virtual files
   - Handles read operations
3. Add resource limits and timeouts
4. Write cross-platform tests
5. Document security model

### References

- FUSE: https://github.com/libfuse/libfuse
- Dokany: https://github.com/dokan-dev/dokany
- macFUSE: https://github.com/osxfuse/osxfuse
- Go FUSE library: https://bazil.org/fuse/

---

## Editor Plugins (Auto-Rebuild on Save)

**Status:** Partially Implemented
**Priority:** High
**Complexity:** Medium

### Description

Editor plugins that provide syntax highlighting and automatically run `iatf rebuild` when user saves an IATF file.

### Platforms to Support

- **VS Code** ✅ **COMPLETED** - [IATF Extension](https://open-vsx.org/extension/Winds-AI/iatf)
  - Syntax highlighting for all IATF elements
  - Color scheme optimized for readability
  - Support for headers, INDEX, CONTENT, references, and code blocks
- Vim/Neovim - Not Started
- Emacs - Not Started
- Sublime Text - Not Started

### How It Would Work

```json
// VS Code extension example (settings.json)
{
  "IATF.autoRebuild": true,
  "IATF.saveTrigger": true
}
```

When user edits and saves `doc.iatf`:
1. Plugin detects save
2. Runs `iatf rebuild doc.iatf` in background
3. Index updated automatically
4. User never needs to manually rebuild

### Benefits

1. **Zero friction** - Index always current
2. **Familiar UX** - Like code formatters (Prettier, Black)
3. **Cross-editor** - Same behavior everywhere
4. **Low complexity** - Just shell out to `IATF` CLI

---

## LSP (Language Server Protocol) Integration

**Status:** Idea / Not Started
**Priority:** Medium
**Complexity:** High

### Description

Implement iatf Language Server for semantic navigation in any LSP-compatible editor.

### Features

| Feature | Description |
|---------|-------------|
| Document Symbols | List all sections in file |
| Go to Definition | Jump to section content from index |
| Find References | Find where section is referenced |
| Hover | Show section metadata on hover |
| Completion | Auto-complete section IDs |

### Example Usage

```bash
# Start LSP server
$ iatf-lsp --stdio < doc.iatf

# Editor sends LSP requests
-> { "jsonrpc": "2.0", "id": 1, "method": "textDocument/documentSymbol", ... }

# Server responds
<- { "jsonrpc": "2.0", "id": 1, "result": [...] }
```

### Benefits

1. **Universal support** - Any LSP-compatible editor (VS Code, Neovim, etc.)
2. **Semantic navigation** - Go to definition, find references
3. **Rich features** - Hover, completion, diagnostics
4. **Standard protocol** - No per-editor plugins needed

---

## Conversion Tools

**Status:** Idea / Not Started
**Priority:** Medium
**Complexity:** Medium

### Description

Tools to convert between iatf and other formats.

| Tool | Purpose |
|------|---------|
| `IATF2md` | IATF â†’ Markdown |
| `md2iatf` | Markdown â†’ IATF |
| `iatf2html` | IATF â†’ HTML (with syntax highlighting) |
| `iatf2json` | IATF â†’ JSON structure |

### Example

```bash
# Convert Markdown to IATF
$ md2iatf README.md > README.iatf

# Convert iatf to HTML
$ iatf2html doc.iatf > doc.html

# Extract IATF structure as JSON
$ iatf2json doc.iatf
{
  "title": "API Guide",
  "sections": [
    {"id": "intro", "title": "Introduction", "lines": "12-20"},
    {"id": "auth", "title": "Authentication", "lines": "22-45"}
  ]
}
```

---

## Web Viewer

**Status:** Idea / Not Started
**Priority:** Low
**Complexity:** High

### Description

Web-based iatf viewer/editor that runs in browser.

### Features

- Upload/view IATF files
- Rendered index with clickable navigation
- Live preview of sections
- Basic editing with auto-rebuild

### Tech Stack

- Frontend: React/Vue
- Backend: Go (for parsing IATF)
- WebAssembly: Compile Go to WASM for client-side parsing

---

## Performance Optimizations

**Status:** Ongoing
**Priority:** Medium

### Ideas

1. **Lazy parsing** - Only parse sections when accessed
2. **Binary index** - Store index in binary format for faster reads
3. **Memory-mapped files** - Use mmap for large IATF files
4. **Incremental rebuild** - Only update changed sections

---

## Section Query Language

**Status:** Idea / Not Started
**Priority:** High
**Complexity:** Low-Medium

### Description

Query language to filter, search, and select sections within IATF files without reading entire content.

### Use Cases

```bash
# Find sections by tag
$ iatf query --tag api doc.iatf

# Sections modified after date
$ iatf query --modified-after 2024-01-01 doc.iatf

# Sections with TODO in content
$ iatf query --content-contains "TODO" doc.iatf

# JSONPath-style queries
$ iatf query '.sections[?(@.level == 1)]' doc.iatf
```

### Query Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `--tag` | Filter by tag | `--tag api,auth` |
| `--author` | Filter by author | `--author "Jane Doe"` |
| `--modified-after` | Date filter | `--modified-after 2024-01-01` |
| `--level` | Section depth | `--level 1-2` |
| `--content-contains` | Full-text search | `--content-contains "TODO"` |
| `--title-match` | Fuzzy title match | `--title-match "intro"` |
| `--id` | Exact section ID | `--id auth-keys` |

### JSON Query Format

```bash
# Query sections matching criteria
$ iatf query --json '.[] | select(.level <= 2) | .title' doc.iatf

# Output
["Introduction", "Authentication", "Installation", "Usage"]
```

### Benefits

1. **Agent efficiency** - Read only relevant sections
2. **Selective analysis** - Focus on changed/new content
3. **Reporting** - Generate reports from documentation
4. **Search** - Find content without full-text indexing

### Implementation

1. Parse index (not full content)
2. Apply filters to section metadata
3. Return matching section IDs and line ranges
4. Optional: Load content for matching sections

---

## Cross-File References and Linking

**Status:** Idea / Not Started
**Priority:** Medium
**Complexity:** Medium

### Description

Allow sections to reference sections in other IATF files, creating linked documentation networks.

### Syntax

```
{#include: other.iatf#section-id}
{#reference: ../api/auth.iatf#authentication}
{#url: https://example.com/docs#intro}
```

### Use Cases

1. **API Documentation** - Reference shared types across files
2. **Modular Docs** - Reusable section content
3. **Knowledge Graphs** - Linked documentation networks
4. **Versioned Docs** - Reference specific versions

### Implementation

```bash
# Parse references in sections
$ iatf resolve-references doc.iatf

# Output dependency graph
doc.iatf:
  {#include: types.iatf#api-types}
  {#reference: auth.iatf#auth-flow}

types.iatf:
  {#api-types}

auth.iatf:
  {#auth-flow}
```

### Challenges

| Challenge | Solution |
|-----------|----------|
| Circular references | Detect and reject during parsing |
| Broken links | Validate all references on rebuild |
| Performance | Cache resolved content |
| Versioning | Pin to specific file versions |

### Benefits

1. **Modular documentation** - Reuse sections across files
2. **Consistent content** - Single source of truth
3. **Linked knowledge** - Navigate between related docs
4. **Maintainable** - Update one file, reflected everywhere

---

## Git Integration and Merge Drivers

**Status:** Idea / Not Started
**Priority:** Medium
**Complexity:** Medium

### Description

Git-aware IATF tools for better version control and collaboration.

### Features

1. **iatf Merge Driver**
   ```
   .gitattributes
   *.iatf merge=iatf-merge-driver
   ```

2. **Three-way merge for sections**
   ```bash
   # Automatic merge for non-conflicting changes
   $ git merge feature-branch

   # Manual resolution for index conflicts
   $ iatf merge --interactive base.iatf main.iatf feature.iatf
   ```

3. **Index-only diffs**
   ```bash
   $ git diff --iatf-index HEAD
   # Show only index changes (content unchanged)
   ```

4. **Smart rebase**
   ```bash
   $ iatf rebase --preserve-index main branch
   # Rebase without breaking index
   ```

### Merge Strategy

```
Base:     Original index
Our:      Our changes
Their:    Their changes

Algorithm:
1. Extract content changes from both sides
2. Rebuild index from changed content
3. Merge indexes (prefer non-conflicting entries)
4. Flag conflicts for manual resolution
```

### Benefits

1. **Better collaboration** - Multiple authors can edit
2. **Smarter diffs** - Index-aware version control
3. **Conflict resolution** - Section-level merge
4. **Audit trail** - Track who changed what and when

---

## Multi-File Projects

**Status:** Idea / Not Started
**Priority:** Medium
**Complexity:** High

### Description

Project format to group multiple IATF files with cross-file operations.

### Project File (atfproj.yaml)

```yaml
name: API Documentation
version: 1.0.0
files:
  - "docs/*.iatf"
settings:
  index-file: docs/index.iatf
  default-section: overview
ignore:
  - "**/drafts/**"
  - "**/*.private.iatf"
```

### Project Commands

```bash
# Create new project
$ iatf project init

# Add file to project
$ iatf project add new-doc.iatf

# Rebuild all files
$ iatf project rebuild

# Cross-file search
$ iatf project search "authentication"

# Generate project index
$ iatf project generate-index

# Validate all files
$ iatf project validate
```

### Cross-File Index

```
Project Index (atfproj-index.json):
{
  "version": "1.0.0",
  "files": [
    {
      "path": "docs/intro.iatf",
      "title": "Introduction",
      "sections": [
        {"id": "getting-started", "title": "Getting Started"},
        {"id": "installation", "title": "Installation"}
      ]
    },
    {
      "path": "docs/auth.iatf",
      "title": "Authentication",
      "sections": [
        {"id": "api-keys", "title": "API Keys"},
        {"id": "oauth", "title": "OAuth 2.0"}
      ]
    }
  ],
  "cross-references": [
    {"from": "intro.iatf#getting-started", "to": "auth.iatf#api-keys"}
  ]
}
```

### Benefits

1. **Organized documentation** - Group related files
2. **Cross-file search** - Search entire project
3. **Unified navigation** - Jump between files
4. **Project-level operations** - Rebuild, validate, search all

---

## Static Site Generation

**Status:** Idea / Not Started
**Priority:** Medium
**Complexity:** High

### Description

Generate static websites from IATF files, similar to Docusaurus/VuePress.

### Usage

```bash
# Generate static site
$ iatf site build --input docs/ --output site/

# Local development server
$ iatf site serve --port 8080

# Preview changes
$ iatf site watch
```

### Output Structure

```
site/
â”œâ”€â”€ index.html          # Landing page
â”œâ”€â”€ intro/
â”‚   â””â”€â”€ index.html      # /intro/ section
â”œâ”€â”€ auth/
â”‚   â””â”€â”€ index.html      # /auth/ section
â”œâ”€â”€ search.json         # Full-text search index
â”œâ”€â”€ sitemap.xml         # SEO sitemap
â””â”€â”€ assets/
    â””â”€â”€ css/
    â””â”€â”€ js/
```

### Features

| Feature | Description |
|---------|-------------|
| Navigation sidebar | Auto-generated from index |
| Full-text search | Client-side search (Lunr.js) |
| Responsive design | Mobile-friendly |
| Dark mode | Theme toggle |
| Syntax highlighting | Code blocks (Prism.js) |
| Print styles | PDF export friendly |

### Theming

```yaml
# iatf-site.yaml
theme:
  name: default
  colors:
    primary: "#3b82f6"
    background: "#ffffff"
  options:
    show-breadcrumbs: true
    show-toc: true
    sidebar-position: left
```

### Benefits

1. **Easy publishing** - Deploy to GitHub Pages, Netlify, Vercel
2. **SEO friendly** - Static HTML, sitemap.xml
3. **Fast loading** - No server-side rendering needed
4. **Offline access** - Works without JavaScript

---

## API/SDK for Programmatic Access

**Status:** Idea / Not Started
**Priority:** High
**Complexity:** Medium

### Description

Libraries for parsing and manipulating IATF files in various programming languages.

### Languages

| Language | Library | Status |
|----------|---------|--------|
| Python | `iatf-lib` | Planned |
| Go | `github.com/Winds-AI/agent-traversal-file` | Planned |
| JavaScript/TypeScript | `@IATF/parser` | Planned |
| Rust | `iatf-rs` | Community |
| Java | `atf4j` | Community |

### Python Example

```python
import IATF

# Parse IATF file
doc = IATF.parse("doc.iatf")

# Access sections
for section in doc.sections:
    print(f"{section.id}: {section.title}")

# Get specific section
intro = doc.get_section("intro")
print(intro.content)

# Modify and save
intro.content = "New content"
doc.save()
```

### Go Example

```go
import "github.com/Winds-AI/agent-traversal-file"

// Parse IATF file
doc, err := IATF.Parse("doc.iatf")
if err != nil {
    log.Fatal(err)
}

// Access sections
for _, section := range doc.Sections {
    fmt.Printf("%s: %s\n", section.ID, section.Title)
}

// Get specific section
intro, _ := doc.GetSection("intro")
fmt.Println(intro.Content)
```

### Core API

| Method | Description |
|--------|-------------|
| `parse(file)` | Parse IATF file |
| `parse_string(content)` | Parse from string |
| `sections` | List all sections |
| `get_section(id)` | Get section by ID |
| `validate()` | Validate IATF structure |
| `rebuild()` | Rebuild index |
| `save(path)` | Save to file |
| `to_json()` | Export as JSON |

### Benefits

1. **Tool integration** - Build IATF-aware tools
2. **Custom workflows** - Script iatf operations
3. **Analysis** - Extract insights from documentation
4. **Migration** - Convert between formats

---

## Section Templates and Snippets

**Status:** Idea / Not Started
**Priority:** Low-Medium
**Complexity:** Low

### Description

Template system for consistent section creation.

### Built-in Templates

```bash
# List available templates
$ iatf template list

# Output
api-endpoint     API endpoint documentation
function         Function documentation
configuration    Configuration option
changelog        Changelog entry
faq              FAQ entry
```

### Create Section from Template

```bash
$ iatf new --template api-endpoint --id users-get --title "Get Users"
```

### Template File

```yaml
# templates/api-endpoint.iatf.j2
{#{{ id }}}
@summary: {{ description }}
@tags: {{ tags | default("api") }}
@created: {{ date }}
@modified: {{ date }}

## {{ title }}

{{ description }}

### Request

```http
{{ method }} {{ path }}
```

### Response

```json
{{ response_example }}
```

{/{{ id }}}
```

### Custom Templates

```bash
# Create custom template
$ iatf template init --path .iatf-templates/

# Add custom template
$ iatf template add custom-template.j2
```

### Benefits

1. **Consistency** - Standardized section structure
2. **Speed** - Faster documentation creation
3. **Completeness** - Templates prompt for required fields
4. **Onboarding** - New contributors follow patterns

---

## Validation and Linting

**Status:** Idea / Not Started
**Priority:** High
**Complexity:** Low-Medium

### Description

Rich validation rules and linting for IATF files.

### Linting Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `section-id-format` | Error | IDs must match `[a-zA-Z][a-zA-Z0-9_-]*` |
| `duplicate-id` | Error | Section IDs must be unique |
| `orphaned-section` | Warning | Section not referenced in index |
| `missing-summary` | Warning | Section should have @summary |
| `depth-exceeded` | Error | Nesting exceeds 2 levels |
| `broken-reference` | Error | Reference to non-existent section |
| `old-modified` | Info | @modified is older than 30 days |
| `long-summary` | Hint | Summary exceeds 80 characters |

### Usage

```bash
# Lint single file
$ iatf lint doc.iatf

# Lint with specific rules
$ iatf lint --rules section-id-format,duplicate-id doc.iatf

# Strict mode (warnings as errors)
$ iatf lint --strict doc.iatf

# JSON output for CI
$ iatf lint --json doc.iatf
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: iatf-lint
        name: iatf Linter
        entry: iatf lint --strict
        files: '\.iatf$'
        language: system
        pass_filenames: true
```

### Custom Rules

```python
# iatf-lint-rules.py
from atf_lint import Rule

class NoTODO(Rule):
    """Sections should not have TODO in content"""

    def check(self, section):
        if "TODO" in section.content:
            return self.warning("TODO found in section content")
        return self.pass_()
```

### Benefits

1. **Quality control** - Consistent documentation
2. **CI integration** - Catch issues in pull requests
3. **Best practices** - Enforce organization standards
4. **Early detection** - Find problems before publishing

---

## Incremental Rebuild and Caching

**Status:** Idea / Not Started
**Priority:** Medium
**Complexity:** Medium

### Description

Only rebuild index for sections that changed, with caching for fast access.

### How It Works

```
Full Rebuild:              Incremental Rebuild:
â”œâ”€ Parse all sections      â”œâ”€ Detect changed sections (via x-hash)
â”œâ”€ Generate index          â”œâ”€ Update only changed entries
â”œâ”€ Update all metadata     â””â”€ Keep cached metadata for unchanged
â””â”€ Write file              â””â”€ Write updated sections only
```

### Cached Metadata

```
.iatf-cache/
â”œâ”€â”€ doc.iatf.json       # Parsed section metadata
â”œâ”€â”€ doc.iatf.index      # Generated index
â””â”€â”€ doc.iatf.hash       # Content hash for change detection
```

### Commands

```bash
# Force full rebuild
$ iatf rebuild --full doc.iatf

# Clear cache
$ iatf rebuild --no-cache doc.iatf

# Show cache stats
$ iatf cache stats
```

### Performance Comparison

| Operation | Full Rebuild | Incremental |
|-----------|--------------|-------------|
| 10 sections | ~50ms | ~10ms |
| 100 sections | ~500ms | ~50ms |
| 1000 sections | ~5s | ~200ms |
| No changes | ~5s | ~1ms |

### Benefits

1. **Faster rebuilds** - Especially for large files
2. **Better UX** - Instant feedback when editing
3. **Resource efficient** - Less CPU/memory for large docs
4. **CI/CD friendly** - Faster builds

---

## AI Model Benchmarking Framework

**Status:** Idea / Not Started
**Priority:** High
**Complexity:** High

### Description

Automated benchmarking system to measure IATF's effectiveness for AI agent navigation compared to traditional tools. Results stored in IATF format for easy comparison and tracking.

### Purpose

1. **Quantify iatf benefits** - Prove iatf is better than alternatives
2. **Model comparison** - Compare different AI models (Claude, GPT-4, etc.)
3. **Tool comparison** - iatf vs grep, traditional grep-like tools, RAG
4. **Track improvements** - Measure progress over time
5. **Guide development** - Identify areas needing optimization

### Benchmark Structure

```
benchmarks/
â”œâ”€â”€ iatf-bench.iatf              # Benchmark configuration and results
â”œâ”€â”€ instructions.iatf           # How to use IATF format
â”œâ”€â”€ test-cases/
â”‚   â”œâ”€â”€ single-pass/
â”‚   â”‚   â”œâ”€â”€ find-info.iatf
â”‚   â”‚   â”œâ”€â”€ extract-code.iatf
â”‚   â”‚   â””â”€â”€ count-sections.iatf
â”‚   â””â”€â”€ agentic/
â”‚       â”œâ”€â”€ multi-step.iatf
â”‚       â”œâ”€â”€ cross-reference.iatf
â”‚       â””â”€â”€ complex-query.iatf
â””â”€â”€ providers/
    â”œâ”€â”€ openai.yaml
    â”œâ”€â”€ anthropic.yaml
    â”œâ”€â”€ google.yaml
    â””â”€â”€ deepseek.yaml
```

### Benchmark IATF file Format

```IATF
:::IATF/1.0
@title: iatf Benchmark Results
@date: 2026-01-22
@benchmark-version: 1.0.0

===INDEX===
# Benchmark Overview {#overview | lines:12-50}
> Summary of all benchmark results

# Single-Pass Tests {#single-pass | lines:52-200}
> Tests for simple information retrieval

## Test: Find API Endpoint {#test-find-api | lines:54-80}
> Locate specific API endpoint in documentation

### Results {#results-find-api | lines:58-75}
| Model | Provider | Context Tokens | Time (ms) | Accuracy |
|-------|----------|----------------|-----------|----------|
| gpt-4o | OpenAI | 4500 | 1200 | 100% |
| claude-3-5-sonnet | Anthropic | 3200 | 980 | 100% |
| gemini-1.5-pro | Google | 5100 | 1500 | 100% |

### Analysis {#analysis-find-api | lines:68-75}
iatf reduced context by 60% compared to full file read.
Time savings: 40% faster with index-based navigation.

# Agentic Tests {#agentic-tests | lines:202-500}
> Complex multi-step reasoning tests

## Test: Cross-Reference Navigation {#test-xref | lines:204-300}
> Find and navigate related sections across files

### Results {#results-xref | lines:208-280}
| Model | Provider | Context Tokens | Time (ms) | Success Rate |
|-------|----------|----------------|-----------|--------------|
| gpt-4o | OpenAI | 8500 | 3500 | 95% |
| claude-3-5-sonnet | Anthropic | 7200 | 3100 | 98% |
| deepseek-v3 | DeepSeek | 9100 | 3800 | 92% |

===CONTENT===

{#benchmark-overview}
@summary: Automated benchmark comparing IATF navigation to traditional approaches
@created: 2026-01-22
@modified: 2026-01-22

# Benchmark Overview

This benchmark measures how effectively AI models can navigate and extract
information from iatf-formatted documents compared to traditional methods.

## Methodology

1. **Test Setup**: Prepare IATF files with varying complexity
2. **Instruction**: Models given specific queries about document content
3. **Baseline**: Measure performance with full file read (traditional approach)
4. **IATF Mode**: Measure performance using iatf index and section extraction
5. **Compare**: Calculate improvements in context, time, and accuracy

## Metrics

| Metric | Description |
|--------|-------------|
| Context Tokens | Tokens sent to model |
| Time | Response latency (ms) |
| Accuracy | Correct answers / Total questions |
| Success Rate | Task completion percentage |

{/benchmark-overview}

{#test-find-api}
@summary: Find specific API endpoint documentation
@tags: api, single-pass, retrieval
@created: 2026-01-22

# Test: Find API Endpoint

## Task
Find the authentication endpoint in the API documentation and extract
its full path, method, and request format.

## Test File
docs/api.iatf

## Query
"What is the authentication endpoint and how do I use it?"

{/test-find-api}
```

### Instructions IATF file

```IATF
:::IATF/1.0
@title: IATF format Instructions for AI Models
@purpose: Guide for AI models on how to navigate IATF files
@created: 2026-01-22

===INDEX===
# How to Use IATF files {#how-to-use | lines:12-80}
> Guide for AI models

# Step 1: Read the Index {#step-1 | lines:14-30}
> Understand document structure

# Step 2: Find Target Section {#step-2 | lines:32-50}
> Locate information using section IDs

# Step 3: Extract Content {#step-3 | lines:52-70}
> Read only the relevant section

# Test Tasks {#test-tasks | lines:72-150}
> Practice tasks for AI models

===CONTENT===

{#how-to-use}
@summary: Guide for AI models on efficiently navigating iatf documents
@tags: guide, tutorial
@created: 2026-01-22

# How to Use IATF files

IATF (Indexed Agent Traversable File) is designed for efficient AI agent navigation.
Instead of reading entire documents, agents can:

1. Read the INDEX section to understand structure
2. Find relevant sections using semantic IDs
3. Extract only the needed content

## Key Concepts

| Concept | Description |
|---------|-------------|
| `{#section-id}` | Opening tag with unique identifier |
| `{/section-id}` | Closing tag |
| `lines:start-end` | Absolute line numbers in file |
| @summary | Section description for quick understanding |

## Example Workflow

```
1. Read lines 4-10 (INDEX section)
2. Find {#authentication} in index
3. Extract lines 25-50 (the authentication section)
4. Answer user query from section content
```

This approach uses 95% less context than reading the full file.

{/how-to-use}

{#step-1}
@summary: Read and understand the INDEX section first

# Step 1: Read the Index

The INDEX section (between ===INDEX=== and ===CONTENT===) contains:

- Section titles with semantic IDs
- Line ranges for each section
- Optional summaries
- Timestamps (created, modified)

## How to Read Index

```bash
# Using iatf CLI
$ iatf index doc.iatf

# Or manually read lines between delimiters
# Find "===" delimiters first
```

## Index Entry Format

```
# Section Title {#section-id | lines:start-end}
> Optional summary text
```

## Example

```
# Authentication {#auth | lines:25-50}
> API authentication methods and tokens
```

This tells you:
- Section title: "Authentication"
- Section ID: "auth"
- Located at lines 25-50 in the file

{/step-1}

{#step-2}
@summary: Find the section containing needed information

# Step 2: Find Target Section

1. Review index entries for relevant titles/summaries
2. Note the section ID and line range
3. The ID follows the format `{#id}`

## Finding Sections

| Query Type | Strategy |
|------------|----------|
| Topic lookup | Match keywords in section titles |
| Specific feature | Search index for feature name |
| Code example | Look for "code" or "example" in summary |
| API endpoint | Search for HTTP method or path |

## Example

Task: Find OAuth 2.0 implementation

```
1. Scan index for "OAuth"
2. Found: ## OAuth 2.0 {#oauth2 | lines:80-120}
3. Note ID: "oauth2"
4. Note lines: 80-120
```

{/step-2}

{#step-3}
@summary: Extract content using section line ranges

# Step 3: Extract Content

Use the line range from the index to read only the relevant section.

## Reading Section Content

```bash
# Using iatf CLI (if available)
$ iatf read doc.iatf oauth2

# Manual extraction
# Read lines 80-120 from file
```

## Section Structure

```
{#section-id}
@summary: Brief description
@tags: keyword1, keyword2
(Content: Markdown, code, etc.)
{/section-id}
```

## Tips

- Sections can be nested (parent/child relationships)
- Look for @tags to understand section topics
- Code examples are usually in their own sections
- Metadata (@created, @modified) shows freshness

{/step-3}

{#test-tasks}
@summary: Practice tasks for AI models

# Test Tasks

Complete these tasks to verify IATF navigation skills:

## Task 1: Simple Lookup
Query: "What is the rate limit for API requests?"
Hint: Search index for "rate" or "limit"

## Task 2: Extract Code
Query: "Show me the Python authentication example"
Hint: Look for "python" or "auth" in tags

## Task 3: Cross-Reference
Query: "What permissions does the admin role have?"
Hint: Check related sections mentioned in summaries

## Task 4: Multi-Step
Query: "Find the error handling section, then show me
        the specific error code for authentication failures"
Hint: Navigate to error section, find auth-related errors

{/test-tasks}
```

### Test Case Categories

#### Single-Pass Tests (Simple Retrieval)

| Test | Description | Difficulty |
|------|-------------|------------|
| Find Info | Locate specific fact in document | Easy |
| Extract Code | Get code example for given language | Easy |
| Count Sections | Count sections matching criteria | Easy |
| List Endpoints | List all API endpoints | Medium |
| Find Definition | Find term definition | Easy |

#### Agentic Tests (Complex Reasoning)

| Test | Description | Difficulty |
|------|-------------|------------|
| Multi-Step | Chain multiple lookups | Hard |
| Cross-Reference | Navigate between related sections | Medium-Hard |
| Complex Query | Answer multi-part question | Hard |
| Comparative | Compare information across sections | Medium |
| Debug Scenario | Find relevant troubleshooting section | Medium |

### Provider Configuration

```yaml
# providers/openai.yaml
provider: openai
models:
  - name: gpt-4o
    context-window: 128000
    max-output: 16384
    api-endpoint: https://api.openai.com/v1
  - name: gpt-4o-mini
    context-window: 128000
    max-output: 16384
```

### Benchmark Commands

```bash
# Run all benchmarks
$ iatf benchmark run --config benchmarks/iatf-bench.iatf

# Run specific test category
$ iatf benchmark run --category single-pass

# Run specific model
$ iatf benchmark run --model gpt-4o

# Compare results
$ iatf benchmark compare --results1 run-2024-01.json --results2 run-2024-02.json

# Generate report
$ iatf benchmark report --format markdown --output benchmark-report.md
```

### Comparison: iatf vs Traditional Approaches

| Aspect | Full File Read | Grep/Search | IATF navigation |
|--------|---------------|-------------|----------------|
| Context Tokens | 100% | 80-90% | 5-20% |
| Time to Answer | Baseline | 1.2x faster | 2-5x faster |
| Accuracy | 100% | 95% | 99% |
| Structured Output | No | No | Yes |
| Section Awareness | No | No | Yes |

### Metrics Collected

| Metric | Description | Collection Method |
|--------|-------------|-------------------|
| Context Tokens | Tokens sent to model | API response |
| Latency | Time from query to answer | Client timer |
| Accuracy | Correct/incorrect answers | Manual verification |
| Success Rate | % of tasks completed | Automated check |
| Token Cost | API cost per query | Provider billing |

### Expected Outcomes

1. **Quantify iatf Benefits**
   - 80-95% reduction in context tokens
   - 2-5x faster response times
   - 99%+ accuracy (improved structure reduces errors)

2. **Model Insights**
   - Which models handle IATF navigation best
   - Optimal prompting strategies per model
   - Context window requirements

3. **Tool Comparison**
   - iatf vs RAG pipelines
   - iatf vs vector search
   - iatf vs traditional grep

### Implementation Roadmap

1. **Phase 1**: Single-pass benchmark runner
2. **Phase 2**: Agentic test cases
3. **Phase 3**: Multi-provider support
4. **Phase 4**: Automated reporting
5. **Phase 5**: Continuous benchmark integration

### Benefits

1. **Proves IATF value** - Data-driven evidence for adoption
2. **Optimizes AI usage** - Find best practices per model
3. **Tracks progress** - Measure improvements over time
4. **Guides development** - Identify bottlenecks
5. **Enables comparison** - iatf vs alternatives

---

## Contributing to Ideas

1. Pick an idea from this file
2. Create a branch: `experiment/your-feature`
3. Implement a proof-of-concept
4. Document findings in this file
5. Open a PR with your experiment

For discussion, open an [Issue](https://github.com/Winds-AI/agent-traversal-file/issues).

---

## Comprehensive Documentation

**Status:** Ongoing
**Priority:** High
**Complexity:** Low-Medium

### Description

Improve documentation with examples, tutorials, and real-world use cases to help users understand IATF.

### Areas to Cover

| Area | Description |
|------|-------------|
| **Getting Started** | 5-minute quick start guide |
| **Tutorial: First IATF file** | Step-by-step tutorial creating your first document |
| **Use Cases** | Real-world examples (API docs, codebooks, design docs) |
| **Best Practices** | Naming conventions, section organization, when to use IATF |
| **Agent Workflows** | How AI agents can use iatf for navigation |
| **Migration Guide** | Converting existing docs to IATF format |
| **Comparison** | iatf vs Markdown, iatf vs Notion, iatf vs Confluence |
| **Troubleshooting** | Common errors and how to fix them |

### Ideas for Content Types

1. **Interactive Tutorial**
   - Web-based step-by-step guide
   - Live iatf editor in browser
   - Immediate feedback

2. **Video Walkthroughs**
   - 3-5 minute videos
   - Installing tools
   - Creating first document
   - Using with AI agents

3. **Example Documents**
   - API documentation template
   - Design document template
   - Codebook template
   - Knowledge base template

4. **Comparison Guides**
   - Why iatf over plain Markdown?
   - When to use iatf vs traditional documentation
   - Agent-friendly documentation patterns

### References

- Good documentation examples: Stripe API docs, Vue.js docs
- Documentation tools: Docusaurus, VitePress, MkDocs

---

## Testing Infrastructure

**Status:** Needs Improvement
**Priority:** High
**Complexity:** Medium

### Current State

- Manual testing via `iatf rebuild` and `iatf validate`
- No automated unit tests for core parsing
- No integration tests for CLI commands

### Goals

| Test Type | Coverage Target | Tools |
|-----------|-----------------|-------|
| Unit Tests | 80% of parsing logic | pytest (Python), testing package (Go) |
| Integration Tests | All CLI commands | Bash scripts, Go's `os/exec` |
| Cross-Platform Tests | Windows, Linux, macOS | GitHub Actions |
| Fuzzing Tests | Malformed input handling | go-fuzz, hypothesis |

### Test Scenarios

1. **Parsing Tests**
   ```python
   def test_parse_content_section():
       lines = [
           "===CONTENT===",
           "{#intro}",
           "@summary: Introduction",
           "# Hello",
           "{/intro}"
       ]
       sections = parse_content_section(lines, 1)
       assert len(sections) == 1
       assert sections[0].id == "intro"
   ```

2. **Rebuild Tests**
   - Test index regeneration preserves data
   - Test x-hash tracking works
   - Test content changes trigger @modified updates

3. **Validation Tests**
   - Valid IATF files pass
   - Invalid IATF files rejected with clear errors
   - Edge cases (empty sections, missing delimiters)

4. **Fuzzing Tests**
   - Random iatf content
   - Malformed inputs
   - Large files (1000+ sections)

### Testing Tools

| Language | Testing Framework |
|----------|-------------------|
| Python | pytest, hypothesis |
| Go | testing package, testify |
| Cross-platform | GitHub Actions matrix |

### CI/CD Integration

```yaml
# GitHub Actions example
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.9", "3.10", "3.11"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - name: Run tests
        run: |
          pip install pytest
          pytest tests/
```

---

## Localization (i18n)

**Status:** Not Started
**Priority:** Low
**Complexity:** Medium

### Description

Add translations for error messages and CLI output to support non-English users.

### Scope

| Component | Localizable? | Notes |
|-----------|--------------|-------|
| CLI error messages | Yes | "Error: File not found" |
| CLI help text | Yes | Command descriptions |
| Validation errors | Yes | "Missing CONTENT section" |
| IATF spec | No | English only (spec is technical) |
| Documentation | Separate repo | Can be localized independently |

### Supported Languages (Goal)

| Language | Status | Contributors |
|----------|--------|--------------|
| English | Default | - |
| Spanish | Needs owner | - |
| Chinese (Simplified) | Needs owner | - |
| Chinese (Traditional) | Needs owner | - |
| Japanese | Needs owner | - |
| German | Needs owner | - |
| French | Needs owner | - |

### Implementation

1. **Message Extraction**
   ```python
   # Instead of:
   print("Error: File not found")

   # Use:
   print(_("Error: File not found"))
   ```

2. **Translation Files**
   ```
   locales/
   â”œâ”€â”€ en_US/
   â”‚   â””â”€â”€ LC_MESSAGES/IATF.po
   â”œâ”€â”€ es_ES/
   â”‚   â””â”€â”€ LC_MESSAGES/IATF.po
   â””â”€â”€ zh_CN/
       â””â”€â”€ LC_MESSAGES/IATF.po
   ```

3. **Tools**
   - Python: `gettext` module
   - Go: `golang.org/x/text/language` + `go-i18n`

### Translation Workflow

1. Extract strings from source code
2. Create `.po` files for each language
3. Community contributes translations
4. PRs for new translations
5. Regular updates as strings change

### Benefits

1. **Accessibility** - Non-English speakers can use IATF
2. **Adoption** - Lower barrier to entry in non-English communities
3. **Community** - Localization is a great entry point for new contributors

### Getting Started

1. Identify all user-facing strings in CLI
2. Set up i18n framework
3. Create template (`.pot`) file
4. Recruit language owners
5. Merge translations via PRs

### References

- GNU gettext: https://www.gnu.org/software/gettext/
- Go i18n: https://github.com/nicksnyder/go-i18n









