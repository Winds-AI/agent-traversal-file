# IATF - Indexed Agent Traversal Format

A file format for agent-friendly document navigation with generated indexes and structured section retrieval.

Status: active development. Breaking changes can occur.

[![Latest Release](https://img.shields.io/github/v/release/Winds-AI/agent-traversal-file)](https://github.com/Winds-AI/agent-traversal-file/releases)
[![Downloads](https://img.shields.io/github/downloads/Winds-AI/agent-traversal-file/total)](https://github.com/Winds-AI/agent-traversal-file/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What IATF Solves

- Avoid loading entire large docs for narrow questions.
- Provide stable section IDs and references (`{@id}`) for traversal.
- Keep INDEX and CONTENT synchronized via rebuild/validate workflows.

## How It Works

IATF stores both:

- `INDEX` (generated navigation layer)
- `CONTENT` (source of truth you edit)

Typical flow:

1. Edit `CONTENT`.
2. Run `iatf rebuild <file>`.
3. Run `iatf validate <file>`.
4. Retrieve using `iatf index`, `iatf find`, `iatf read`, `iatf read-many`, `iatf graph`.

## Measured Efficiency (Current)

Token efficiency is conditional and workload-dependent.

From `docs/reports/agentic-usability-analysis.md`:
- On sparse retrieval for a large fixture: ~64% fewer tokens vs full-file reads.
- On medium files with broad reads: index-first can be similar to full-file cost.

Use index-first flows when retrieval is selective and reference topology matters.

## Installation

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.sh | sudo bash
```

### Windows (PowerShell as Administrator)

```powershell
irm https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.ps1 | iex
```

## Quick Example

```bash
iatf rebuild examples/incident-playbook.iatf
iatf validate examples/incident-playbook.iatf
iatf index examples/incident-playbook.iatf
iatf find examples/incident-playbook.iatf "rollback"
iatf read examples/incident-playbook.iatf rollback
iatf read-many examples/incident-playbook.iatf detect rollback postmortem
```

## Documentation

Start here: `docs/README.md`

Key docs:
- `docs/QUICKSTART.md`
- `docs/COMMANDS.md`
- `docs/SPECIFICATION.md`
- `docs/DEVELOPMENT.md`
- `docs/testing.md`
- `docs/reports/agentic-usability-analysis.md`

Archive (historical/exploratory):
- `docs/archive/IDEAS.md`
- `docs/archive/TASKS.md`

## License

MIT License. See `LICENSE`.
