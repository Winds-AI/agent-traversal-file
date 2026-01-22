# ATF - Agent Traversable File

**A file format designed for AI agents to efficiently navigate large documents.**

> **📍 Project Location:** `S:\Random_stuff\agent-traversal-file`
> **📝 Abbreviation:** ATF (Agent Traversable File)

[![Latest Release](https://img.shields.io/github/v/release/atf-tools/atf)](https://github.com/atf-tools/atf/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## The Problem

AI agents struggle with large documents:
- ❌ **Token limits** - Can't load entire 10,000-line documents
- ❌ **Wasted tokens** - Loading everything to find one section
- ❌ **No navigation** - No standardized way to jump to sections
- ❌ **No references** - No way to reference sections to other sections reliably.
- ❌ **Blind loading** - Must read content to know what it contains

At least till someone solves long term memory.

If your question is WHY? THEN
yes we can use folder and file structure to define multiple nested files so that we don't have to use .atf but i don't like that and it's hard to navigate for me and my ADHD brain said let's build a overengineered solution for this.

We can also use JSON's and MD's with seperate index file but that will not be much useful in long running tasks, the goal here is to function as a kind of harness for a model so that if it updates the content section or any human updates the content section, the index should be updated automatically and the scope of work or any document stays aligned. Sure for now agent can corrupt a file because training data does not have enough info about the standard so i am exploring that space also to make agentic coding more efficient in any way possible.

## About Me

I am not a high level software engineer, i am just a guy who likes AI Assisted coding to build things and explore new ideas.
Idea is mine but ALL of the code in this is written and tested by either claude or codex so it can have bugs. I am open to critisms and suggestions about this idea.

## The Solution

ATF provides a **self-indexing document format** with two regions:

```
┌─────────────────────────────────────────┐
│ INDEX (Auto-generated)                  │
│  • Section titles & summaries           │
│  • Line numbers for each section        │
│  • Created & modified dates             │
│  • ~5% of document size                 │
├─────────────────────────────────────────┤
│ CONTENT (Source of truth)               │
│  • Full document text                   │
│  • Organized into sections              │
│  • Edit freely - index auto-rebuilds    │
└─────────────────────────────────────────┘
```

**Agents save 80-95% tokens** by loading only the INDEX, then fetching specific sections as needed.

---

## Quick Start

### Installation

**macOS/Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/atf-tools/atf/main/install/install.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/atf-tools/atf/main/install/install.ps1 | iex
```

**Or download binary directly:**
- [Windows](https://github.com/atf-tools/atf/releases/latest/download/atf-windows-amd64.exe)
- [macOS Intel](https://github.com/atf-tools/atf/releases/latest/download/atf-darwin-amd64)
- [macOS Apple Silicon](https://github.com/atf-tools/atf/releases/latest/download/atf-darwin-arm64)
- [Linux](https://github.com/atf-tools/atf/releases/latest/download/atf-linux-amd64)

### Usage

```bash
# Rebuild index for a single file
atf rebuild document.atf

# Rebuild all .atf files in directory
atf rebuild-all

# Watch file and auto-rebuild on save
atf watch document.atf

# Stop watching a file
atf unwatch document.atf

# Validate file structure
atf validate document.atf
```

---

## Example

**Create an ATF file:**

```
:::ATF/1.0
@title: My Documentation

===CONTENT===

{#intro}
@summary: Overview of the project
@created: 2025-01-20
@modified: 2025-01-20
# Introduction

This is my documentation content...
{/intro}

{#setup}
@summary: Installation and setup instructions
@created: 2025-01-20
@modified: 2025-01-20
# Setup

Follow these steps to install...
{/setup}
```

**Run the rebuild:**

```bash
atf rebuild my-doc.atf
```

**Result - Auto-generated INDEX:**

```
===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT -->
<!-- Generated: 2025-01-20T10:30:00Z -->

# Introduction {#intro | lines:12-18}
> Overview of the project
  Created: 2025-01-20 | Modified: 2025-01-20

# Setup {#setup | lines:20-26}
> Installation and setup instructions
  Created: 2025-01-20 | Modified: 2025-01-20
```

**Agents can now:**
1. Read INDEX (18 lines) instead of full document (26+ lines)
2. See summaries of each section
3. Load only needed sections by line number

---

## Key Features

| Feature | Benefit |
|---------|---------|
| **Auto-generated INDEX** | Edit content freely, index updates automatically |
| **Section summaries** | Agents understand content without loading it |
| **Line-based addressing** | Direct access to sections via line numbers |
| **Timestamps per section** | Track when content was created/modified |
| **Plain text format** | Human-readable, works with any editor |
| **Watch mode** | Auto-rebuild on save during development |

---

## How Agents Use ATF

```python
# Agent workflow
# 1. Load INDEX (small, ~5% of file)
index = read_file("docs.atf", lines=1, limit=50)

# 2. Parse INDEX to find relevant sections
# "User asked about authentication"
# INDEX shows: "# Auth {#auth | lines:120-180}"

# 3. Load only that section
section = read_file("docs.atf", lines=120, limit=61)

# 4. Answer question
# Used ~100 lines instead of 1000+ lines = 90% token savings
```

---

## Commands Reference

### `atf rebuild <file>`

Rebuild index for a single file.

```bash
atf rebuild document.atf
```

### `atf rebuild-all [directory]`

Rebuild all `.atf` files in a directory (recursive).

```bash
atf rebuild-all              # Current directory
atf rebuild-all ./docs       # Specific directory
atf rebuild-all --exclude node_modules
```

### `atf watch <file>`

Watch a file and auto-rebuild when it changes. **Watch continues until:**
- You run `atf unwatch <file>`
- You close the terminal (process ends)
- System restarts (process ends)

```bash
# Start watching
atf watch document.atf

# In another terminal, edit document.atf and save
# Index rebuilds automatically!

# Stop watching
atf unwatch document.atf
```

**Watch mode runs in the foreground** - keep the terminal open while watching.

### `atf unwatch <file>`

Stop watching a specific file.

```bash
atf unwatch document.atf
```

**List all watched files:**
```bash
atf watch --list
```

### `atf validate <file>`

Check if an ATF file is valid.

```bash
atf validate document.atf
```

**Checks:**
- Has format declaration (`:::ATF/1.0`)
- Has INDEX section (warns if missing)
- Has CONTENT section
- INDEX/CONTENT sections are unique and ordered correctly
- INDEX Content-Hash matches CONTENT (warns if missing)
- INDEX entries match CONTENT sections and line ranges
- CONTENT has no lines outside section blocks
- All section IDs are unique
- All sections are properly closed

**Exit codes:**
- `0` - File is valid
- `1` - File has errors

---

## File Format Specification

See [SPECIFICATION.md](SPECIFICATION.md) for complete details.

### Minimal Example

```
:::ATF/1.0
@title: Document Title

===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT -->

# Section {#section-id | lines:10-15}
> Section summary
  Created: 2025-01-20 | Modified: 2025-01-20

===CONTENT===

{#section-id}
@summary: Section summary
@created: 2025-01-20
@modified: 2025-01-20
# Section

Content goes here...
{/section-id}
```

### Section Metadata

Each section can have:
- `@summary:` - Brief description (shown in INDEX)
- `@created:` - Creation date (YYYY-MM-DD)
- `@modified:` - Last modification date (YYYY-MM-DD)

All are optional but recommended.

**Nesting limit:** This implementation enforces a maximum depth of 2 (section + subsection).

---

## Watch Mode Details

**Question: How long does watch mode run?**

**Answer:** Watch runs in the foreground and stops when:

1. **You explicitly stop it:** `atf unwatch <file>`
2. **You press Ctrl+C**
3. **Terminal closes**

**Check what's being watched:**
```bash
atf watch --list

# Output:
# Watching 2 files:
#   /path/to/document.atf (since 2025-01-20 10:30:00)
#   /path/to/other.atf (since 2025-01-20 11:15:00)
```

---

## Use Cases

### API Documentation

```
Single 5,000-line API reference
→ Agent loads 250-line INDEX
→ Finds "Authentication" section at lines 120-340
→ Loads just that section
→ 95% token savings
```

### Knowledge Base

```
Team wiki with 100 sections
→ Agent scans INDEX to find relevant topics
→ Loads only 2-3 relevant sections
→ Answers question with fraction of tokens
```

### Product Specifications

```
50-page product spec
→ Agent loads INDEX, sees all sections
→ User asks about "Performance Requirements"
→ Agent loads just that section
→ Fast, efficient, precise
```

---

## Development

### Python Implementation

```bash
cd python
python atf.py rebuild document.atf
```

See [python/README.md](python/README.md) for details.

### Go Implementation

```bash
cd go
go run main.go rebuild document.atf
```

See [go/README.md](go/README.md) for details.

### Building from Source

```bash
# Ensure Go is in your PATH

# Build for your platform
go build -o atf main.go

# Run commands
./atf rebuild document.atf
./atf validate document.atf

# Cross-compile for all platforms
./build.sh
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

**Areas where we need help:**
- [ ] VS Code extension
- [ ] Vim/Neovim plugin
- [ ] Language Server Protocol (LSP) implementation
- [ ] Conversion tools (Markdown → ATF, HTML → ATF)
- [ ] Documentation and examples

---

## Comparison with Other Formats

| Format | Human Readable | Agent Navigation | Self-Indexing | Token Efficient |
|--------|----------------|------------------|---------------|-----------------|
| **Markdown** | ✅ | ❌ | ❌ | ❌ |
| **HTML** | ~ | ~ | ❌ | ❌ |
| **PDF** | ~ | ❌ | ❌ | ❌ |
| **ATF** | ✅ | ✅ | ✅ | ✅ |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Links

- **Specification:** [SPECIFICATION.md](SPECIFICATION.md)
- **Problem Statement:** [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)
- **Design Decisions:** [docs/DESIGN.md](docs/DESIGN.md)
- **Usage Guide:** [docs/USAGE.md](docs/USAGE.md)
- **GitHub Releases:** [Latest Release](https://github.com/atf-tools/atf/releases/latest)

---

**Made with ❤️ for AI agents and the humans who work with them.**
