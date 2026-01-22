# ATF Tools - Quick Start Guide

Get started with ATF in 5 minutes!

---

## Installation

Choose your platform:

### macOS/Linux
```bash
curl -fsSL https://raw.githubusercontent.com/atf-tools/atf/main/install/install.sh | bash
```

### Windows
```powershell
irm https://raw.githubusercontent.com/atf-tools/atf/main/install/install.ps1 | iex
```

### Verify Installation
```bash
atf --version
```

---

## Your First ATF File

### 1. Create a file: `my-doc.atf`

```
:::ATF/1.0
@title: My First ATF Document

===CONTENT===

{#intro}
@summary: Introduction to my document
@created: 2025-01-20
@modified: 2025-01-20
# Introduction

This is my first ATF document!

It has sections that can be auto-indexed.
{/intro}

{#details}
@summary: More detailed information
@created: 2025-01-20
@modified: 2025-01-20
# Details

Here's some more content in a separate section.

ATF will auto-generate an index for this!
{/details}
```

### 2. Rebuild the Index

```bash
atf rebuild my-doc.atf
```

### 3. See the Result

Open `my-doc.atf` and you'll see the auto-generated INDEX:

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
atf watch my-doc.atf
```

Now every time you save `my-doc.atf`, the index rebuilds automatically!

**To stop watching:**
```bash
atf unwatch my-doc.atf
```

---

## All Commands

```bash
# Rebuild single file
atf rebuild document.atf

# Rebuild all .atf files in directory
atf rebuild-all ./docs

# Watch and auto-rebuild
atf watch document.atf

# Stop watching
atf unwatch document.atf

# List watched files
atf watch --list

# Validate file
atf validate document.atf

# Show help
atf --help
```

---

## How AI Agents Use ATF

**Traditional approach (wasteful):**
```python
# Agent loads entire 5,000-line document
content = read_file("docs.md")  # 6,000 tokens!
# Find relevant section by parsing everything
answer = extract_section(content, "authentication")
```

**ATF approach (efficient):**
```python
# Agent loads only the INDEX (250 lines)
index = read_file("docs.atf", lines=1, limit=250)  # 300 tokens

# Find section in INDEX
section = find_section(index, "authentication")
# → "Authentication at lines 120-180"

# Load just that section
auth_content = read_file("docs.atf", lines=120, limit=61)  # 600 tokens

# Total: 900 tokens instead of 6,000 = 85% savings!
```

---

## Tips

1. **Section IDs**: Use descriptive IDs like `auth-oauth` instead of `section1`
2. **Summaries**: Always add `@summary:` - agents rely on these!
3. **Timestamps**: Update `@modified:` when you change a section
4. **Watch mode**: Keep it running while writing docs
5. **Validate often**: Run `atf validate` to catch errors early

---

## What's Next?

- **Read the full specification**: [SPECIFICATION.md](SPECIFICATION.md)
- **See examples**: Check out [examples/](examples/) folder
- **Understand the problem**: Read [docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)
- **Contribute**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Getting Help

- **Documentation**: https://github.com/atf-tools/atf
- **Issues**: https://github.com/atf-tools/atf/issues
- **Discussions**: https://github.com/atf-tools/atf/discussions

---

**You're all set! Start creating efficient, agent-friendly documentation!** 🚀
