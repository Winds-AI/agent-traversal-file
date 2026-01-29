# IATF - Indexed Agent Traversable File

**A file format designed for AI agents to efficiently navigate large documents.**
[In Active Development so expect Breaking Changes]

> **Abbreviation:** IATF (Indexed Agent Traversable File)

[![Latest Release](https://img.shields.io/github/v/release/Winds-AI/agent-traversal-file)](https://github.com/Winds-AI/agent-traversal-file/releases)
[![Downloads](https://img.shields.io/github/downloads/Winds-AI/agent-traversal-file/total)](https://github.com/Winds-AI/agent-traversal-file/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Winds-AI/agent-traversal-file)

---

## The Problem

AI agents struggle with large documents:
- **Token limits** - Can't load entire 10,000-line documents
- **Wasted tokens** - Loading everything to find one section
- **No navigation** - No standardized way to jump to sections
- **No references** - No way to reference sections to other sections reliably
- **Blind loading** - Must read content to know what it contains

At least till someone solves long term memory.

If your question is WHY? THEN
yes we can use folder and file structure to define multiple nested files so that we don't have to use .iatf but i don't like that and it's hard to navigate for me and my ADHD brain said let's build a overengineered solution for this.

We can also use JSON's and MD's with seperate index file but that will not be much useful in long running tasks, the goal here is to function as a kind of harness for a model so that if it updates the content section or any human updates the content section, the index should be updated automatically and the scope of work or any document stays aligned. Sure for now agent can corrupt a file because training data does not have enough info about the standard so i am exploring that space also to make agentic coding more efficient in any way possible.

## About Me

I am not a high level software engineer, i am just a guy who likes AI Assisted coding to build things and explore new ideas.
Idea is mine but ALL of the code in this is written and tested by either claude or codex so it can have bugs. I am open to critisms and suggestions about this idea.

## The Solution

IATF provides a **self-indexing document format** with two regions:

```
+----------------------------------------+
| INDEX (Auto-generated)                 |
|  * Section titles & summaries           |
|  * Line numbers for each section        |
|  * Created & modified dates             |
|  * ~5% of document size                 |
|----------------------------------------|
| CONTENT (Source of truth)              |
|  * Full document text                   |
|  * Organized into sections              |
|  * Edit freely - index auto-rebuilds    |
+----------------------------------------+
```

**Agents save 80-95% tokens** by loading only the INDEX, then fetching specific sections as needed.

---

## Quick Start

### Installation

**Quick Install (Recommended):**

Run this one-line command to download and install automatically:

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.sh | sudo bash
```

**Windows (PowerShell as Administrator):**
```powershell
irm https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.ps1 | iex
```

**Manual Installation:**

Visit [GitHub Releases](https://github.com/Winds-AI/agent-traversal-file/releases/latest) to download the binary for your platform:

- Windows: `iatf-windows-amd64.exe`
- macOS Intel: `iatf-darwin-amd64`
- macOS Apple Silicon: `iatf-darwin-arm64`
- Linux x86_64: `iatf-linux-amd64`
- Linux ARM64: `iatf-linux-arm64`

**After downloading the binary:**

**Linux/macOS:**
```bash
# Navigate to download location
cd ~/Downloads

# Make executable and install
chmod +x iatf-*
sudo mv iatf-* /usr/local/bin/iatf

# Verify installation
iatf --version
```

**Windows:**
1. Rename `iatf-windows-amd64.exe` to `iatf.exe`
2. Move to a folder (e.g., `C:\Program Files\IATF\`)
3. Add that folder to your system PATH:
   - Search "Environment Variables" in Start menu
   - Edit "Path" under System variables
   - Add the folder path
   - Restart terminal

**VSCode Extension (Optional):**

For syntax highlighting in VSCode, install the IATF extension:
- **Marketplace:** [IATF Extension](https://open-vsx.org/extension/Winds-AI/iatf)
- **Features:** Syntax highlighting for headers, sections, index entries, references, and code blocks

### Usage

```bash
# Rebuild index for a single file
iatf rebuild document.iatf

# Rebuild all .iatf files in directory
iatf rebuild-all

# Watch file and auto-rebuild on save
iatf watch document.iatf

# Stop watching a file
iatf unwatch document.iatf

# Validate file structure
iatf validate document.iatf

# Show section reference graph
iatf graph document.iatf
```

### Verify Installation

```bash
iatf --version
iatf --help
```

### Uninstalling

**If installed via script:**

```bash
# Linux/macOS (system-wide)
sudo rm /usr/local/bin/iatf

# Linux/macOS (user-local)
rm ~/.local/bin/iatf
```

```powershell
# Windows (PowerShell as Administrator)
Remove-Item "C:\Program Files\IATF\iatf.exe"
# Or user-local
Remove-Item "$env:USERPROFILE\bin\iatf.exe"
```

**If installed manually:**
```bash
# Linux/macOS - remove from wherever you placed it
sudo rm /usr/local/bin/iatf

# Windows - delete the folder you created and remove from PATH
```

---

## Example

**Create an IATF file:**

```
:::IATF
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

Follow these steps to install. See {@intro} for context.
{/setup}
```

**Run the rebuild:**

```bash
iatf rebuild my-doc.iatf
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
| **Section references** | In-content cross-references using `{@section-id}` validated at build time |
| **Plain text format** | Human-readable, works with any editor |
| **Watch mode** | Auto-rebuild on save during development |

---

## How Agents Use IATF

```python
# Agent workflow
# 1. Load INDEX (small, ~5% of file)
index = read_file("docs.iatf", lines=1, limit=50)

# 2. Parse INDEX to find relevant sections
# "User asked about authentication"
# INDEX shows: "# Auth {#auth | lines:120-180}"

# 3. Load only that section
section = read_file("docs.iatf", lines=120, limit=61)

# 4. Answer question
# Used ~100 lines instead of 1000+ lines = 90% token savings
```

---

## Commands Reference

### `iatf rebuild <file>`

Rebuild index for a single file.

```bash
iatf rebuild document.iatf
```

### `iatf rebuild-all [directory]`

Rebuild all `.iatf` files in a directory (recursive).

```bash
iatf rebuild-all              # Current directory
iatf rebuild-all ./docs       # Specific directory
iatf rebuild-all --exclude node_modules
```

### `iatf watch <file>`

Watch a file and auto-rebuild when it changes. **Watch continues until:**
- You run `iatf unwatch <file>`
- You close the terminal (process ends)
- System restarts (process ends)

```bash
# Start watching
iatf watch document.iatf

# In another terminal, edit document.iatf and save
# Index rebuilds automatically!

# Stop watching
iatf unwatch document.iatf
```

**Watch mode runs in the foreground** - keep the terminal open while watching.

**Rebuild warning:** If you run `iatf rebuild` on a file that's being watched, you'll see a warning:
```
Warning: This file is being watched by another process (PID 12345)
A manual rebuild will trigger an automatic rebuild from the watch process.
This will cause the file to be rebuilt twice.

Continue with manual rebuild? [y/N]:
```
This prevents accidental double rebuilds. Press `y` to proceed anyway, or `n` to cancel.

### `iatf unwatch <file>`

Stop watching a specific file.

```bash
iatf unwatch document.iatf
```

**List all watched files:**
```bash
iatf watch --list
```

### `iatf validate <file>`

Check if an IATF file is valid.

```bash
iatf validate document.iatf
```

**Checks:**
- Has format declaration (`:::IATF`)
- Has INDEX section (warns if missing)
- Has CONTENT section
- INDEX/CONTENT sections are unique and ordered correctly
- INDEX Content-Hash matches CONTENT (warns if missing)
- INDEX entries match CONTENT sections and line ranges
- CONTENT has no lines outside section blocks
- All section IDs are unique
- All sections are properly closed
- All section references are valid (Check 9)

**Exit codes:**
- `0` - File is valid
- `1` - File has errors

### `iatf graph <file> [--show-incoming]`

Display section cross-reference graph in compact text format. Requires an INDEX section.

```bash
# Show outgoing references (default)
iatf graph document.iatf

# Show incoming references (impact analysis)
iatf graph document.iatf --show-incoming
```

**Default (outgoing references):**
- Shows what each section references via `{@section-id}`
- Arrow direction: `section -> what-it-references`
- Use for: Reading path, understanding dependencies

**Example output:**
```text
@graph: document.iatf

intro -> setup, auth
setup -> prerequisites
auth -> setup, security-model
api-endpoints -> auth, data-models
deployment -> auth, api-endpoints
troubleshooting
```

**With `--show-incoming` flag:**
- Shows who references each section
- Arrow direction: `section <- who-references-it`
- Use for: Impact analysis, "what will break if I change this?"

**Example output:**
```text
@graph: document.iatf

intro
setup <- intro, auth
auth <- intro, api-endpoints, deployment
prerequisites <- setup
security-model <- auth
api-endpoints <- deployment
data-models <- api-endpoints
deployment
troubleshooting
```

**Use cases:**
- **Reading path** (outgoing): Understand which sections to read first
- **Impact analysis** (incoming): See what sections will be affected by changes
- **Navigation**: Build a mental map of document structure
- **Dependencies**: Track conceptual relationships

**Note:** For hierarchy (parent-child containment), use `iatf index` instead. The `graph` command shows only cross-references made via `{@section-id}` syntax.

---

## File Format Specification

See [SPECIFICATION.md](SPECIFICATION.md) for complete details.

### Minimal Example

```
:::IATF
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

### Section References

Use `{@section-id}` inside section content to cross-reference other sections (for example, "See `{@setup}` for installation details."). References are validated during `iatf rebuild` and `iatf validate`: a reference must point to an existing section, and a section cannot reference itself. The validator ignores references inside fenced code blocks only when the fence line is exactly ``` (no language tag). For full rules and examples, see [SPECIFICATION.md](SPECIFICATION.md#13a-section-references).

---

## Watch Mode Details

**Question: How long does watch mode run?**

**Answer:** Watch runs in the foreground and stops when:

1. **You explicitly stop it:** `iatf unwatch <file>`
2. **You press Ctrl+C**
3. **Terminal closes**

**Check what's being watched:**
```bash
iatf watch --list

# Output:
# Watching 2 files:
#   /path/to/document.iatf (since 2025-01-20 10:30:00)
#   /path/to/other.iatf (since 2025-01-20 11:15:00)
```

**Watch state file:** `~/.iatf/watch.json` tracks watched files and their PIDs for the rebuild warning feature.

---

## Use Cases

### API Documentation

```
Single 5,000-line API reference
-> Agent loads 250-line INDEX
-> Finds "Authentication" section at lines 120-340
-> Loads just that section
-> 95% token savings
```

### Knowledge Base

```
Team wiki with 100 sections
-> Agent scans INDEX to find relevant topics
-> Loads only 2-3 relevant sections
-> Answers question with fraction of tokens
```

### Product Specifications

```
50-page product spec
-> Agent loads INDEX, sees all sections
-> User asks about "Performance Requirements"
-> Agent loads just that section
-> Fast, efficient, precise
```

---

## Development

### Building from Source

```bash
cd go
go run main.go rebuild document.iatf
```

See [go/README.md](go/README.md) for details.

### Building from Source

**Prerequisites:** Go 1.21+

```bash
# Clone the repository
git clone https://github.com/Winds-AI/agent-traversal-file.git
cd agent-traversal-file

# Build for your platform
cd go
go build -o iatf main.go

# Run commands
./iatf rebuild ../examples/simple.iatf
./iatf validate ../examples/simple.iatf
```

**For releases:** We use [GoReleaser](https://goreleaser.com). See [GORELEASER_MIGRATION.md](GORELEASER_MIGRATION.md) for details.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

**Areas where we need help:**
- [x] VS Code extension ([Available](https://open-vsx.org/extension/Winds-AI/iatf))
- [ ] Vim/Neovim plugin
- [ ] Language Server Protocol (LSP) implementation
- [ ] Conversion tools (Markdown -> IATF, HTML -> IATF)
- [ ] Documentation and examples

---

## Comparison with Other Formats

| Format | Human Readable | Agent Navigation | Self-Indexing | Token Efficient |
|--------|----------------|------------------|---------------|-----------------|
| **Markdown** | Yes | No | No | No |
| **HTML** | ~ | ~ | No | No |
| **PDF** | ~ | No | No | No |
| **IATF** | Yes | Yes | Yes | Yes |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Links

- **Specification:** [SPECIFICATION.md](SPECIFICATION.md)
- **Problem Statement:** [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)
- **Design Decisions:** [docs/DESIGN.md](docs/DESIGN.md)
- **Usage Guide:** [docs/USAGE.md](docs/USAGE.md)
- **GitHub Releases:** [Latest Release](https://github.com/Winds-AI/agent-traversal-file/releases/latest)

---

**Made with love for AI agents and the humans who work with them.**




