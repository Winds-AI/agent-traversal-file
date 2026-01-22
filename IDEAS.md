# Ideas & Future Directions

This file contains experimental ideas and proposed features. These are not implemented yet and may require significant work. Feel free to pick one and start experimenting!

---

## FUSE/Dokany/macFUSE Filesystem Mounting

**Status:** Idea / Not Started  
**Priority:** Low-Medium  
**Complexity:** High

### Description

Mount ATF files as virtual filesystems so standard tools (cat, grep, wc, ls) can work directly with sections without needing the `atf` CLI tool.

### Platforms

| Platform | Library |
|----------|---------|
| Linux | FUSE |
| Windows | Dokany |
| macOS | macFUSE |

### How It Would Work

```bash
# Mount ATF file as filesystem
$ atf-fuse doc.atf /mnt/atf

# Access sections as files/directories
$ ls /mnt/atf/
index  content/

$ cat /mnt/atf/index
# Auto-generated index (always current)

$ cat /mnt/atf/content/intro
# {#intro} section content

$ cat /mnt/atf/content/auth-keys
# {#auth-keys} section content

# Standard tools work natively
$ grep "TODO" /mnt/atf/content/*
$ wc -l /mnt/atf/content/*
```

### Virtual Structure

```
/mnt/atf/
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
4. **Transparent** - User sees filesystem, not ATF format

### Concerns

| Issue | Details |
|-------|---------|
| **Performance** | 20-100x slower than native filesystem (4 context switches per operation) |
| **Security** | Malicious ATF could cause resource exhaustion, path traversal |
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
   - Validate ATF structure before mounting
   - Reject malformed files

### Implementation Steps

1. Choose FUSE library (Go has `bazil.org/fuse`, Python has `fuse-python`)
2. Implement filesystem driver that:
   - Parses ATF file on mount
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

**Status:** Idea / Not Started  
**Priority:** High  
**Complexity:** Medium

### Description

Editor plugins that automatically run `atf rebuild` when user saves an ATF file.

### Platforms to Support

- VS Code
- Vim/Neovim
- Emacs
- Sublime Text

### How It Would Work

```json
// VS Code extension example (settings.json)
{
  "atf.autoRebuild": true,
  "atf.saveTrigger": true
}
```

When user edits and saves `doc.atf`:
1. Plugin detects save
2. Runs `atf rebuild doc.atf` in background
3. Index updated automatically
4. User never needs to manually rebuild

### Benefits

1. **Zero friction** - Index always current
2. **Familiar UX** - Like code formatters (Prettier, Black)
3. **Cross-editor** - Same behavior everywhere
4. **Low complexity** - Just shell out to `atf` CLI

---

## LSP (Language Server Protocol) Integration

**Status:** Idea / Not Started  
**Priority:** Medium  
**Complexity:** High

### Description

Implement ATF Language Server for semantic navigation in any LSP-compatible editor.

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
$ atf-lsp --stdio < doc.atf

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

Tools to convert between ATF and other formats.

| Tool | Purpose |
|------|---------|
| `atf2md` | ATF → Markdown |
| `md2atf` | Markdown → ATF |
| `atf2html` | ATF → HTML (with syntax highlighting) |
| `atf2json` | ATF → JSON structure |

### Example

```bash
# Convert Markdown to ATF
$ md2atf README.md > README.atf

# Convert ATF to HTML
$ atf2html doc.atf > doc.html

# Extract ATF structure as JSON
$ atf2json doc.atf
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

Web-based ATF viewer/editor that runs in browser.

### Features

- Upload/view ATF files
- Rendered index with clickable navigation
- Live preview of sections
- Basic editing with auto-rebuild

### Tech Stack

- Frontend: React/Vue
- Backend: Go (for parsing ATF)
- WebAssembly: Compile Go to WASM for client-side parsing

---

## Performance Optimizations

**Status:** Ongoing  
**Priority:** Medium

### Ideas

1. **Lazy parsing** - Only parse sections when accessed
2. **Binary index** - Store index in binary format for faster reads
3. **Memory-mapped files** - Use mmap for large ATF files
4. **Incremental rebuild** - Only update changed sections

---

## Section Query Language

**Status:** Idea / Not Started  
**Priority:** High  
**Complexity:** Low-Medium

### Description

Query language to filter, search, and select sections within ATF files without reading entire content.

### Use Cases

```bash
# Find sections by tag
$ atf query --tag api doc.atf

# Sections modified after date
$ atf query --modified-after 2024-01-01 doc.atf

# Sections with TODO in content
$ atf query --content-contains "TODO" doc.atf

# JSONPath-style queries
$ atf query '.sections[?(@.level == 1)]' doc.atf
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
$ atf query --json '.[] | select(.level <= 2) | .title' doc.atf

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

Allow sections to reference sections in other ATF files, creating linked documentation networks.

### Syntax

```
{#include: other.atf#section-id}
{#reference: ../api/auth.atf#authentication}
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
$ atf resolve-references doc.atf

# Output dependency graph
doc.atf:
  {#include: types.atf#api-types}
  {#reference: auth.atf#auth-flow}

types.atf:
  {#api-types}

auth.atf:
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

Git-aware ATF tools for better version control and collaboration.

### Features

1. **ATF Merge Driver**
   ```
   .gitattributes
   *.atf merge=atf-merge-driver
   ```

2. **Three-way merge for sections**
   ```bash
   # Automatic merge for non-conflicting changes
   $ git merge feature-branch
   
   # Manual resolution for index conflicts
   $ atf merge --interactive base.atf main.atf feature.atf
   ```

3. **Index-only diffs**
   ```bash
   $ git diff --atf-index HEAD
   # Show only index changes (content unchanged)
   ```

4. **Smart rebase**
   ```bash
   $ atf rebase --preserve-index main branch
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

Project format to group multiple ATF files with cross-file operations.

### Project File (atfproj.yaml)

```yaml
name: API Documentation
version: 1.0.0
files:
  - "docs/*.atf"
settings:
  index-file: docs/index.atf
  default-section: overview
ignore:
  - "**/drafts/**"
  - "**/*.private.atf"
```

### Project Commands

```bash
# Create new project
$ atf project init

# Add file to project
$ atf project add new-doc.atf

# Rebuild all files
$ atf project rebuild

# Cross-file search
$ atf project search "authentication"

# Generate project index
$ atf project generate-index

# Validate all files
$ atf project validate
```

### Cross-File Index

```
Project Index (atfproj-index.json):
{
  "version": "1.0.0",
  "files": [
    {
      "path": "docs/intro.atf",
      "title": "Introduction",
      "sections": [
        {"id": "getting-started", "title": "Getting Started"},
        {"id": "installation", "title": "Installation"}
      ]
    },
    {
      "path": "docs/auth.atf",
      "title": "Authentication",
      "sections": [
        {"id": "api-keys", "title": "API Keys"},
        {"id": "oauth", "title": "OAuth 2.0"}
      ]
    }
  ],
  "cross-references": [
    {"from": "intro.atf#getting-started", "to": "auth.atf#api-keys"}
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

Generate static websites from ATF files, similar to Docusaurus/VuePress.

### Usage

```bash
# Generate static site
$ atf site build --input docs/ --output site/

# Local development server
$ atf site serve --port 8080

# Preview changes
$ atf site watch
```

### Output Structure

```
site/
├── index.html          # Landing page
├── intro/
│   └── index.html      # /intro/ section
├── auth/
│   └── index.html      # /auth/ section
├── search.json         # Full-text search index
├── sitemap.xml         # SEO sitemap
└── assets/
    └── css/
    └── js/
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
# atf-site.yaml
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

Libraries for parsing and manipulating ATF files in various programming languages.

### Languages

| Language | Library | Status |
|----------|---------|--------|
| Python | `atf-lib` | Planned |
| Go | `github.com/atf-tools/atf` | Planned |
| JavaScript/TypeScript | `@atf/parser` | Planned |
| Rust | `atf-rs` | Community |
| Java | `atf4j` | Community |

### Python Example

```python
import atf

# Parse ATF file
doc = atf.parse("doc.atf")

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
import "github.com/atf-tools/atf"

// Parse ATF file
doc, err := atf.Parse("doc.atf")
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
| `parse(file)` | Parse ATF file |
| `parse_string(content)` | Parse from string |
| `sections` | List all sections |
| `get_section(id)` | Get section by ID |
| `validate()` | Validate ATF structure |
| `rebuild()` | Rebuild index |
| `save(path)` | Save to file |
| `to_json()` | Export as JSON |

### Benefits

1. **Tool integration** - Build ATF-aware tools
2. **Custom workflows** - Script ATF operations
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
$ atf template list

# Output
api-endpoint     API endpoint documentation
function         Function documentation
configuration    Configuration option
changelog        Changelog entry
faq              FAQ entry
```

### Create Section from Template

```bash
$ atf new --template api-endpoint --id users-get --title "Get Users"
```

### Template File

```yaml
# templates/api-endpoint.atf.j2
{#{{ id }}}
@summary: {{ description }}
@tags: {{ tags | default("api") }}
@author: {{ author }}
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
$ atf template init --path .atf-templates/

# Add custom template
$ atf template add custom-template.j2
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

Rich validation rules and linting for ATF files.

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
$ atf lint doc.atf

# Lint with specific rules
$ atf lint --rules section-id-format,duplicate-id doc.atf

# Strict mode (warnings as errors)
$ atf lint --strict doc.atf

# JSON output for CI
$ atf lint --json doc.atf
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: atf-lint
        name: ATF Linter
        entry: atf lint --strict
        files: '\.atf$'
        language: system
        pass_filenames: true
```

### Custom Rules

```python
# atf-lint-rules.py
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
├─ Parse all sections      ├─ Detect changed sections (via x-hash)
├─ Generate index          ├─ Update only changed entries
├─ Update all metadata     └─ Keep cached metadata for unchanged
└─ Write file              └─ Write updated sections only
```

### Cached Metadata

```
.atf-cache/
├── doc.atf.json       # Parsed section metadata
├── doc.atf.index      # Generated index
└── doc.atf.hash       # Content hash for change detection
```

### Commands

```bash
# Force full rebuild
$ atf rebuild --full doc.atf

# Clear cache
$ atf rebuild --no-cache doc.atf

# Show cache stats
$ atf cache stats
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

Automated benchmarking system to measure ATF's effectiveness for AI agent navigation compared to traditional tools. Results stored in ATF format for easy comparison and tracking.

### Purpose

1. **Quantify ATF benefits** - Prove ATF is better than alternatives
2. **Model comparison** - Compare different AI models (Claude, GPT-4, etc.)
3. **Tool comparison** - ATF vs grep, traditional grep-like tools, RAG
4. **Track improvements** - Measure progress over time
5. **Guide development** - Identify areas needing optimization

### Benchmark Structure

```
benchmarks/
├── atf-bench.atf              # Benchmark configuration and results
├── instructions.atf           # How to use ATF format
├── test-cases/
│   ├── single-pass/
│   │   ├── find-info.atf
│   │   ├── extract-code.atf
│   │   └── count-sections.atf
│   └── agentic/
│       ├── multi-step.atf
│       ├── cross-reference.atf
│       └── complex-query.atf
└── providers/
    ├── openai.yaml
    ├── anthropic.yaml
    ├── google.yaml
    └── deepseek.yaml
```

### Benchmark ATF File Format

```atf
:::ATF/1.0
@title: ATF Benchmark Results
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
ATF reduced context by 60% compared to full file read.
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
@summary: Automated benchmark comparing ATF navigation to traditional approaches
@created: 2026-01-22
@modified: 2026-01-22

# Benchmark Overview

This benchmark measures how effectively AI models can navigate and extract
information from ATF-formatted documents compared to traditional methods.

## Methodology

1. **Test Setup**: Prepare ATF files with varying complexity
2. **Instruction**: Models given specific queries about document content
3. **Baseline**: Measure performance with full file read (traditional approach)
4. **ATF Mode**: Measure performance using ATF index and section extraction
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
docs/api.atf

## Query
"What is the authentication endpoint and how do I use it?"

{/test-find-api}
```

### Instructions ATF File

```atf
:::ATF/1.0
@title: ATF Format Instructions for AI Models
@purpose: Guide for AI models on how to navigate ATF files
@created: 2026-01-22

===INDEX===
# How to Use ATF Files {#how-to-use | lines:12-80}
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
@summary: Guide for AI models on efficiently navigating ATF documents
@tags: guide, tutorial
@created: 2026-01-22

# How to Use ATF Files

ATF (Agent Traversal File) is designed for efficient AI agent navigation.
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
# Using atf CLI
$ atf index doc.atf

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
# Using atf CLI (if available)
$ atf read doc.atf oauth2

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

Complete these tasks to verify ATF navigation skills:

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
$ atf benchmark run --config benchmarks/atf-bench.atf

# Run specific test category
$ atf benchmark run --category single-pass

# Run specific model
$ atf benchmark run --model gpt-4o

# Compare results
$ atf benchmark compare --results1 run-2024-01.json --results2 run-2024-02.json

# Generate report
$ atf benchmark report --format markdown --output benchmark-report.md
```

### Comparison: ATF vs Traditional Approaches

| Aspect | Full File Read | Grep/Search | ATF Navigation |
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

1. **Quantify ATF Benefits**
   - 80-95% reduction in context tokens
   - 2-5x faster response times
   - 99%+ accuracy (improved structure reduces errors)

2. **Model Insights**
   - Which models handle ATF navigation best
   - Optimal prompting strategies per model
   - Context window requirements

3. **Tool Comparison**
   - ATF vs RAG pipelines
   - ATF vs vector search
   - ATF vs traditional grep

### Implementation Roadmap

1. **Phase 1**: Single-pass benchmark runner
2. **Phase 2**: Agentic test cases
3. **Phase 3**: Multi-provider support
4. **Phase 4**: Automated reporting
5. **Phase 5**: Continuous benchmark integration

### Benefits

1. **Proves ATF value** - Data-driven evidence for adoption
2. **Optimizes AI usage** - Find best practices per model
3. **Tracks progress** - Measure improvements over time
4. **Guides development** - Identify bottlenecks
5. **Enables comparison** - ATF vs alternatives

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

Improve documentation with examples, tutorials, and real-world use cases to help users understand ATF.

### Areas to Cover

| Area | Description |
|------|-------------|
| **Getting Started** | 5-minute quick start guide |
| **Tutorial: First ATF File** | Step-by-step tutorial creating your first document |
| **Use Cases** | Real-world examples (API docs, codebooks, design docs) |
| **Best Practices** | Naming conventions, section organization, when to use ATF |
| **Agent Workflows** | How AI agents can use ATF for navigation |
| **Migration Guide** | Converting existing docs to ATF format |
| **Comparison** | ATF vs Markdown, ATF vs Notion, ATF vs Confluence |
| **Troubleshooting** | Common errors and how to fix them |

### Ideas for Content Types

1. **Interactive Tutorial**
   - Web-based step-by-step guide
   - Live ATF editor in browser
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
   - Why ATF over plain Markdown?
   - When to use ATF vs traditional documentation
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

- Manual testing via `atf rebuild` and `atf validate`
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
   - Valid ATF files pass
   - Invalid ATF files rejected with clear errors
   - Edge cases (empty sections, missing delimiters)

4. **Fuzzing Tests**
   - Random ATF content
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
| ATF spec | No | English only (spec is technical) |
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
   ├── en_US/
   │   └── LC_MESSAGES/atf.po
   ├── es_ES/
   │   └── LC_MESSAGES/atf.po
   └── zh_CN/
       └── LC_MESSAGES/atf.po
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

1. **Accessibility** - Non-English speakers can use ATF
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
