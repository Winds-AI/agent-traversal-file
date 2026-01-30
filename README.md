# IATF - Indexed Agent Traversal Format

**A file format designed for AI agents to efficiently navigate large documents.**
[In Active Development and Research so expect Breaking Changes]

> **Abbreviation:** IATF (Indexed Agent Traversal Format)

[![Latest Release](https://img.shields.io/github/v/release/Winds-AI/agent-traversal-file)](https://github.com/Winds-AI/agent-traversal-file/releases)
[![Downloads](https://img.shields.io/github/downloads/Winds-AI/agent-traversal-file/total)](https://github.com/Winds-AI/agent-traversal-file/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Winds-AI/agent-traversal-file)

## ALL Docs

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for:
- Quick installation
- Creating your first IATF file
- How AI agents use IATF

See [docs/COMMANDS.md](docs/COMMANDS.md) for:
- All CLI commands and options
- Watch mode for single files and directories
- System-wide daemon for continuous monitoring
- Workflow examples and common patterns

See [docs/SPECIFICATION.md](docs/SPECIFICATION.md) for complete details on:
- File format specification
- Section metadata and references
- INDEX and CONTENT structure

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for:
- Contribution guidelines
- Areas where help is needed

See [docs/IDEAS.md](docs/IDEAS.md) for:
- Experimental ideas and proposed features

See [docs/TASKS.md](docs/TASKS.md) for:
- Current and completed development tasks

See [LICENSE](LICENSE) for MIT License details.

See [GitHub Releases](https://github.com/Winds-AI/agent-traversal-file/releases/latest) to download binaries and changelogs.

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

## Installation

### Quick Install (Recommended)

Run this one-line command to download and install automatically:

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.sh | sudo bash
```

**Windows (PowerShell as Administrator):**
```powershell
irm https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.ps1 | iex
```

**VSCode Extension (Optional):**

For syntax highlighting in VSCode, install the IATF extension:
- **Marketplace:** [IATF Extension](https://open-vsx.org/extension/Winds-AI/iatf)
- **Features:** Syntax highlighting for headers, sections, index entries, references, and code blocks


---

**How to use with Agents:**

I have defined a skill for iatf file format , though i will recommend not to use skills, just extract the content and use it as a simple md file and include a reference of this file in your main AGENTS.md or CLAUDE.md. This will be more helpful as this is not a specialized skill for one task, it needs to be used when the this format files are involved so you want need all te skill name, description, progressive disclosure because that will distract it more in this case.

---


## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Made with love for AI agents and the humans who work with them.**



