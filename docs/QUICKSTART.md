# IATF Tools - Quick Start Guide

Get started with IATF in 5 minutes!

---

## Installation

### Quick Install

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.sh | sudo bash
```

**Windows (PowerShell as Administrator):**
```powershell
irm https://raw.githubusercontent.com/Winds-AI/agent-traversal-file/main/installers/install.ps1 | iex
```

For manual installation, alternative install methods, and uninstalling, see [COMMANDS.md](./COMMANDS.md#installation--setup).

---

## Your First IATF File

### 1. Open the example file: `examples/incident-playbook.iatf`

This repo includes a ready-made example we'll use throughout this guide.

```
{#incident}
@summary: Incident response timeline template
# Incident Timeline

- T+00m: Detect alert and declare incident
- T+05m: Assign incident commander and scribe
...
{/incident}
```

### 2. Rebuild the Index

```bash
iatf rebuild examples/incident-playbook.iatf
```

### 3. See the Result

Open `examples/incident-playbook.iatf` and you'll see the auto-generated INDEX:

```
===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
<!-- Generated: 2026-01-30T09:52:01Z -->
<!-- Content-Hash: sha256:c761c92 -->

# Incident Timeline {#incident | lines:28-40 | words:50}
> Incident response timeline template
  Created: 2025-01-20 | Modified: 2026-01-30

# Rollback Steps {#rollback | lines:42-57 | words:44}
> Rollback steps with commands
  Created: 2025-01-20 | Modified: 2026-01-30

# Action Items {#postmortem | lines:59-73 | words:45}
> Post-incident writeup outline
  Created: 2025-01-20 | Modified: 2026-01-30
```

**Agents can now:**
1. Read the INDEX instead of the full document
2. See summaries of each section
3. Load only needed sections by line number

---

## How AI Agents Use IATF

**Traditional approach (wasteful):**
```bash
# Agent loads entire 5,000-line document
content = read_file("docs.md")  # 6,000 tokens!
# Find relevant section by parsing everything
answer = extract_section(content, "rollback")
```

**IATF approach (efficient):**

**Step 1: Discover available topics**
```bash
iatf index examples/incident-playbook.iatf | rg -i 'incident|rollback|postmortem'
# Output:
# # Incident Timeline {#incident | lines:28-40 | words:50}
# > Incident response timeline template
# # Rollback Steps {#rollback | lines:42-57 | words:44}
# > Rollback steps with commands
# # Action Items {#postmortem | lines:59-73 | words:45}
# > Post-incident writeup outline
```

**Step 2: Check dependencies before implementing**
```bash
iatf graph examples/incident-playbook.iatf | rg '^incident'
# Output:
# incident -> postmortem, rollback
```

**Step 3: Analyze impact before editing**
```bash
iatf graph examples/incident-playbook.iatf --show-incoming | rg '^postmortem'
# Output:
# postmortem <- incident, rollback
```

**Step 4: Load only the needed section**
```bash
iatf read examples/incident-playbook.iatf rollback
# Returns only lines 42-57 (Rollback section)
# Contains: rollback steps and commands
```

**Total: far fewer tokens than reading the full file.**

**Plus validation:** All sections are automatically validated on save, so agents know the content is syntactically correct and references are valid.

**Key advantages:**
- **Fast discovery**: iatf index is ~5% of document size
- **Precise navigation**: Exact line numbers from INDEX
- **Reference safety**: {@section-id} references are validated
- **Automatic updates**: Changes to CONTENT auto-update INDEX
- **Safe for agents**: Validation prevents broken references

---

## More Agent Command Patterns (Incident Playbook)

**Find a topic and open first match:**
```bash
id=$(iatf index examples/incident-playbook.iatf | rg -i rollback | head -1 | rg -o '#[A-Za-z0-9_-]+' | sed 's/^#//')
iatf read examples/incident-playbook.iatf "$id"
```

**Open every matching section:**
```bash
iatf index examples/incident-playbook.iatf | rg -i 'incident|rollback' | rg -o '#[A-Za-z0-9_-]+' | sed 's/^#//' | xargs -n1 iatf read examples/incident-playbook.iatf
```

**Show outgoing references for a section:**
```bash
iatf graph examples/incident-playbook.iatf | rg '^incident'
```

**Show incoming references for a section:**
```bash
iatf graph examples/incident-playbook.iatf --show-incoming | rg '^postmortem'
```

**Extract references mentioned inside a section:**
```bash
iatf read examples/incident-playbook.iatf incident | rg -o '\\{@[A-Za-z0-9_-]+\\}' | tr -d '{@}' | sort -u
```

**Fallback without iatf CLI (read by INDEX line numbers):**
```bash
rg '^# .*\\{#rollback' examples/incident-playbook.iatf
# Example output contains: lines:42-57
sed -n '42,57p' examples/incident-playbook.iatf
```

---

## Tips

1. **Section IDs**: Use descriptive IDs like `rollback` instead of `section1`
2. **Summaries**: Always add `@summary:` - agents rely on these!
3. **Timestamps**: Update `@modified:` when you change a section
4. **Section references**: Link between sections with `{@section-id}` syntax

---

## What's Next?

- **Command reference**: See [COMMANDS.md](./COMMANDS.md) for all CLI commands
- **Read the full specification**: [SPECIFICATION.md](./SPECIFICATION.md)
- **See examples**: Check out [examples/](../examples/) folder
- **Contribute**: See [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## Getting Help

- **Documentation**: https://github.com/Winds-AI/agent-traversal-file
- **Issues**: https://github.com/Winds-AI/agent-traversal-file/issues
---

**You're all set! Start creating efficient, agent-friendly documentation!**




