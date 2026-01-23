# IATF Tools - Quick Start Guide

Get started with IATF in 5 minutes!

---

## Installation

Choose your platform:

### macOS/Linux
```bash
curl -fsSL https://raw.githubusercontent.com/iatf-tools/iatf/main/install/install.sh | bash
```

### Windows
```powershell
irm https://raw.githubusercontent.com/iatf-tools/iatf/main/install/install.ps1 | iex
```

### Verify Installation
```bash
iatf --version
```

---

## Your First IATF File

### 1. Create a file: `my-doc.iatf`

```
:::IATF/1.0
@title: My First IATF Document

===CONTENT===

{#intro}
@summary: Introduction to my document
@created: 2025-01-20
@modified: 2025-01-20
# Introduction

This is my first IATF document!

It has sections that can be auto-indexed.
{/intro}

{#details}
@summary: More detailed information
@created: 2025-01-20
@modified: 2025-01-20
# Details

Here's some more content in a separate section.

IATF will auto-generate an index for this!
{/details}
```

### 2. Rebuild the Index

```bash
iatf rebuild my-doc.iatf
```

### 3. See the Result

Open `my-doc.iatf` and you'll see the auto-generated INDEX:

```
===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT -->
<!-- Generated: 2025-01-20T10:30:00Z -->

# Introduction {#intro | lines:10-17}
> Introduction to my document
  Created: 2025-01-20 | Modified: 2025-01-20

# Details {#details | lines:19-26}
> More detailed information
  Created: 2025-01-20 | Modified: 2025-01-20
```

---

## Using Watch Mode

While editing, use watch mode to auto-rebuild:

```bash
iatf watch my-doc.iatf
```

Now every time you save `my-doc.iatf`, the index rebuilds automatically!

**To stop watching:**
```bash
iatf unwatch my-doc.iatf
```

---

## All Commands

```bash
# Rebuild single file
iatf rebuild document.iatf

# Rebuild all .iatf files in directory
iatf rebuild-all ./docs

# Watch and auto-rebuild
iatf watch document.iatf

# Stop watching
iatf unwatch document.iatf

# List watched files
iatf watch --list

# Validate file
iatf validate document.iatf

# Show help
iatf --help
```

---

## How AI Agents Use IATF

**Traditional approach (wasteful):**
```python
# Agent loads entire 5,000-line document
content = read_file("docs.md")  # 6,000 tokens!
# Find relevant section by parsing everything
answer = extract_section(content, "authentication")
```

**IATF approach (efficient):**
```python
# Agent loads only the INDEX (250 lines)
index = read_file("docs.iatf", lines=1, limit=250)  # 300 tokens

# Find section in INDEX
section = find_section(index, "authentication")
# â†’ "Authentication at lines 120-180"

# Load just that section
auth_content = read_file("docs.iatf", lines=120, limit=61)  # 600 tokens

# Total: 900 tokens instead of 6,000 = 85% savings!
```

---

## Tips

1. **Section IDs**: Use descriptive IDs like `auth-oauth` instead of `section1`
2. **Summaries**: Always add `@summary:` - agents rely on these!
3. **Timestamps**: Update `@modified:` when you change a section
4. **Watch mode**: Keep it running while writing docs
5. **Validate often**: Run `iatf validate` to catch errors early

---

## What's Next?

- **Read the full specification**: [SPECIFICATION.md](SPECIFICATION.md)
- **See examples**: Check out [examples/](examples/) folder
- **Understand the problem**: Read [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)
- **Contribute**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Getting Help

- **Documentation**: https://github.com/iatf-tools/iatf
- **Issues**: https://github.com/iatf-tools/iatf/issues
- **Discussions**: https://github.com/iatf-tools/iatf/discussions

---

**You're all set! Start creating efficient, agent-friendly documentation!** ðŸš€







