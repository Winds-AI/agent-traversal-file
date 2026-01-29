# IATF VS Code Extension

Syntax highlighting for IATF (Indexed Agent Traversable File) format.

## Installation

Install from the marketplace:
- **Marketplace:** [IATF Extension](https://marketplace.windsurf.com/extension/Winds-AI/iatf)
- **Publisher:** Winds-AI
- **Extension ID:** `Winds-AI.iatf`

## Features

- **Format declarations:** `:::IATF/1.0` header syntax
- **Section delimiters:** `===INDEX===` and `===CONTENT===` markers
- **Index entries:** Headings, section IDs, line ranges, word counts, timestamps, and hashes
- **Content blocks:** `{#section-id}` opening and `{/section-id}` closing tags
- **References:** `{@section-id}` cross-references with link-like highlighting
- **Metadata:** `@summary:`, `@created:`, `@modified:` annotations
- **Code fences:** ` ``` ` delimiter highlighting
- **Comments:** `<!-- -->` HTML-style comments
- **Optimized colors:** Carefully chosen color scheme for readability and visual hierarchy

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
- **Specification:** [SPECIFICATION.md](https://github.com/Winds-AI/agent-traversal-file/blob/main/SPECIFICATION.md)
- **Quick Start:** [QUICKSTART.md](https://github.com/Winds-AI/agent-traversal-file/blob/main/QUICKSTART.md)

## License

MIT License - see [LICENSE](https://github.com/Winds-AI/agent-traversal-file/blob/main/LICENSE)
