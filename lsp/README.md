# IATF Language Server

A Language Server Protocol (LSP) implementation for IATF files, providing IDE features like diagnostics, navigation, and auto-completion.

## Features

| Feature | Description |
|---------|-------------|
| **Diagnostics** | Real-time validation errors and warnings |
| **Go to Definition** | Jump from `{@ref}` to `{#section}` with F12 or Ctrl+Click |
| **Find References** | Find all references to a section with Shift+F12 |
| **Hover** | Show section summary and metadata on hover |
| **Auto-completion** | Complete section IDs after typing `{@` |
| **Document Symbols** | Outline view showing all sections |

## Installation

### Option 1: Build from Source

```bash
cd lsp
go build -o bin/iatf-lsp .
```

For cross-platform builds:

```bash
# Windows
GOOS=windows GOARCH=amd64 go build -o bin/iatf-lsp.exe .

# macOS (Intel)
GOOS=darwin GOARCH=amd64 go build -o bin/iatf-lsp-darwin .

# macOS (Apple Silicon)
GOOS=darwin GOARCH=arm64 go build -o bin/iatf-lsp-darwin-arm64 .

# Linux
GOOS=linux GOARCH=amd64 go build -o bin/iatf-lsp-linux .
```

### Option 2: Install via Go

```bash
go install github.com/Winds-AI/agent-traversal-file/lsp@latest
```

This installs `iatf-lsp` to `$GOPATH/bin`.

## Usage with VSCode

The IATF VSCode extension automatically discovers the LSP server if it's:
1. In the extension's `bin/` folder
2. In `$GOPATH/bin`
3. In your system `PATH`

You can also configure the path manually:

```json
{
  "iatf.lsp.enabled": true,
  "iatf.lsp.path": "/path/to/iatf-lsp"
}
```

## Usage with Other Editors

The LSP server communicates over stdio and follows the Language Server Protocol 3.16 specification.

### Neovim (with nvim-lspconfig)

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

if not configs.iatf then
  configs.iatf = {
    default_config = {
      cmd = { 'iatf-lsp' },
      filetypes = { 'iatf' },
      root_dir = function(fname)
        return lspconfig.util.find_git_ancestor(fname) or vim.fn.getcwd()
      end,
      settings = {},
    },
  }
end

lspconfig.iatf.setup{}
```

### Helix

Add to `~/.config/helix/languages.toml`:

```toml
[[language]]
name = "iatf"
scope = "source.iatf"
file-types = ["iatf"]
language-servers = ["iatf-lsp"]

[language-server.iatf-lsp]
command = "iatf-lsp"
```

### Sublime Text (with LSP package)

Add to LSP settings:

```json
{
  "clients": {
    "iatf": {
      "enabled": true,
      "command": ["iatf-lsp"],
      "selector": "source.iatf"
    }
  }
}
```

## LSP Capabilities

The server implements these LSP methods:

| Method | Description |
|--------|-------------|
| `initialize` | Server initialization and capability negotiation |
| `textDocument/didOpen` | Document opened notification |
| `textDocument/didChange` | Document content change notification |
| `textDocument/didClose` | Document closed notification |
| `textDocument/didSave` | Document saved notification |
| `textDocument/publishDiagnostics` | Publish validation diagnostics |
| `textDocument/completion` | Provide completion items |
| `textDocument/hover` | Provide hover information |
| `textDocument/definition` | Go to definition |
| `textDocument/references` | Find all references |
| `textDocument/documentSymbol` | Document outline symbols |

## Validation Rules

The LSP server validates:

- Format declaration (`:::IATF`)
- INDEX and CONTENT section presence
- Section nesting (max 2 levels)
- Duplicate section IDs
- Unclosed sections
- Mismatched open/close tags
- Invalid references (non-existent targets)
- Self-references

## Development

### Project Structure

```
lsp/
├── main.go              # LSP server entry point and handlers
├── analyzer/
│   └── analyzer.go      # IATF document parsing and analysis
├── go.mod
├── go.sum
└── bin/                 # Build output directory
```

### Building

```bash
cd lsp
go mod tidy
go build -o bin/iatf-lsp .
```

### Testing

```bash
go test ./...
```

### Running in Debug Mode

The server logs to stderr. To see debug output:

```bash
./bin/iatf-lsp 2>&1 | tee lsp.log
```

## Protocol Details

### Transport

The server uses stdio transport:
- Reads JSON-RPC messages from stdin
- Writes JSON-RPC responses to stdout
- Logs debug information to stderr

### Message Format

Standard LSP JSON-RPC 2.0 format:

```json
Content-Length: <length>\r\n
\r\n
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...}}
```

## Dependencies

- [tliron/glsp](https://github.com/tliron/glsp) - Go Language Server Protocol SDK
- [tliron/commonlog](https://github.com/tliron/commonlog) - Logging utilities
