# IATF VS Code Extension

Full language support for IATF (Indexed Agent Traversal Format) with syntax highlighting, validation, navigation, and intelligent code completion.

## Installation

Install from the marketplace:
- **Marketplace:** [IATF Extension](https://marketplace.windsurf.com/extension/Winds-AI/iatf)
- **Publisher:** Winds-AI
- **Extension ID:** `Winds-AI.iatf`

## Features

### Syntax Highlighting
- **Format declarations:** `:::IATF` header syntax
- **Section delimiters:** `===INDEX===` and `===CONTENT===` markers
- **Index entries:** Headings, section IDs, line ranges, word counts, timestamps, and hashes
- **Content blocks:** `{#section-id}` opening and `{/section-id}` closing tags
- **References:** `{@section-id}` cross-references with link-like highlighting
- **Metadata:** `@summary:`, `@created:`, `@modified:` annotations
- **Code fences:** ` ``` ` delimiter highlighting
- **Comments:** `<!-- -->` HTML-style comments

### Language Server Features (with iatf-lsp)

When the IATF Language Server is installed, you get:

| Feature | Description | Shortcut |
|---------|-------------|----------|
| **Real-time Diagnostics** | Validation errors and warnings as you type | Automatic |
| **Go to Definition** | Jump from `{@ref}` to `{#section}` | F12 or Ctrl+Click |
| **Find All References** | Find all references to a section | Shift+F12 |
| **Hover Information** | Show section summary on hover | Hover over tag |
| **Auto-completion** | Complete section IDs after `{@` | Ctrl+Space |
| **Document Outline** | See all sections in the outline view | Ctrl+Shift+O |

### Installing the Language Server

The extension automatically discovers the LSP server. Install it with:

```bash
# Build from source
cd lsp
go build -o bin/iatf-lsp .

# Or install via Go
go install github.com/Winds-AI/agent-traversal-file/lsp@latest
```

## Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `iatf.lsp.enabled` | boolean | `true` | Enable the language server |
| `iatf.lsp.path` | string | `""` | Custom path to iatf-lsp executable |

Example settings.json:
```json
{
  "iatf.lsp.enabled": true,
  "iatf.lsp.path": "/usr/local/bin/iatf-lsp"
}
```

## Color Scheme

The extension uses a semantic color scheme designed for dark themes:
- **Section delimiters** - Bright magenta (structural landmarks)
- **Section IDs** - Gold (easy to track across INDEX and CONTENT)
- **References** - Bright cyan with underline (link-like appearance)
- **Metadata** - Light blue (distinguishable from content)
- **Line numbers & timestamps** - Light green (standard numeric values)

## About IATF

IATF is a file format designed for AI agents to efficiently navigate large documents. Learn more:

- **Repository:** [https://github.com/Winds-AI/agent-traversal-file](https://github.com/Winds-AI/agent-traversal-file)
- **Specification:** [SPECIFICATION.md](https://github.com/Winds-AI/agent-traversal-file/blob/main/docs/SPECIFICATION.md)
- **Quick Start:** [QUICKSTART.md](https://github.com/Winds-AI/agent-traversal-file/blob/main/docs/QUICKSTART.md)
- **LSP Server:** [lsp/README.md](https://github.com/Winds-AI/agent-traversal-file/blob/main/lsp/README.md)

## Changelog

### v0.1.0
- Added Language Server Protocol (LSP) integration
- Added real-time validation and diagnostics
- Added go-to-definition for references
- Added find-all-references
- Added hover information
- Added auto-completion for section IDs
- Added document outline/symbols

### v0.0.5
- Initial release with syntax highlighting
- Section colorization with unique colors per ID

## License

MIT License - see [LICENSE](https://github.com/Winds-AI/agent-traversal-file/blob/main/LICENSE)
