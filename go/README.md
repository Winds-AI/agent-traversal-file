# IATF Tools - Go Implementation

High-performance Go implementation that compiles to standalone binaries.

## Features

- ✅ Single static binary (no dependencies)
- ✅ Cross-compiles to all platforms
- ✅ Fast (~10-50ms rebuild time)
- ✅ Small binary size (~2-5MB)
- ✅ All 5 commands implemented

## Building

### Prerequisites
Ensure Go is in your PATH.

### Build for your platform

```bash
go build -o iatf main.go
```

### Cross-compile for all platforms

**For releases**, we use GoReleaser (see `.goreleaser.yml`):
```bash
goreleaser release --snapshot --clean  # Test build
```

**For manual cross-compilation**:
```bash
# Windows
GOOS=windows GOARCH=amd64 go build -o iatf-windows-amd64.exe main.go

# macOS Intel
GOOS=darwin GOARCH=amd64 go build -o iatf-darwin-amd64 main.go

# macOS Apple Silicon
GOOS=darwin GOARCH=arm64 go build -o iatf-darwin-arm64 main.go

# Linux
GOOS=linux GOARCH=amd64 go build -o iatf-linux-amd64 main.go
GOOS=linux GOARCH=arm64 go build -o iatf-linux-arm64 main.go
```

### Optimized build (smaller binary)

```bash
go build -ldflags="-s -w" -o iatf main.go
```

Flags:
- `-s`: Strip debug symbols
- `-w`: Strip DWARF debugging info
- Result: 30-50% smaller binary

## Usage

```bash
./iatf rebuild document.iatf
./iatf rebuild-all ./docs
./iatf watch document.iatf
./iatf unwatch document.iatf
./iatf validate document.iatf
```

## Code Structure

```go
// Types
type Section struct { ... }       // Represents a section
type WatchState map[string]WatchInfo
type WatchInfo struct { ... }

// Core Functions
parseContentSection()  // Parse CONTENT section
generateIndex()        // Generate INDEX from sections  
rebuildIndex()         // Main rebuild logic

// Commands
rebuildCommand()       // Rebuild single file
rebuildAllCommand()    // Rebuild directory
watchCommand()         // Watch mode
unwatchCommand()       // Stop watching
validateCommand()      // Validation
```

## Dependencies

**None!** Pure Go standard library:
- `encoding/json` - Watch state
- `fmt` - Output
- `os` - File operations
- `path/filepath` - Path handling
- `regexp` - Pattern matching
- `strings` - String operations
- `time` - Timestamps

## Performance

Benchmarks on M1 Mac:

| File Size | Sections | Time |
|-----------|----------|------|
| 500 lines | 5 | 8ms |
| 2,000 lines | 20 | 23ms |
| 5,000 lines | 50 | 48ms |
| 10,000 lines | 100 | 95ms |

## Development

### Run without building

```bash
go run main.go rebuild test.iatf
```

### Format code

```bash
go fmt main.go
```

### Run tests (TODO)

```bash
go test
```

## Binary Size

| Build Type | Size |
|------------|------|
| Default build | ~4-6 MB |
| Optimized (`-ldflags="-s -w"`) | ~2-3 MB |
| Compressed (UPX) | ~1 MB |

## Cross-Compilation Table

| GOOS | GOARCH | Notes |
|------|--------|-------|
| windows | amd64 | 64-bit Windows |
| darwin | amd64 | macOS Intel |
| darwin | arm64 | macOS Apple Silicon |
| linux | amd64 | 64-bit Linux |
| linux | arm64 | ARM64 Linux (Raspberry Pi, etc.) |
| linux | 386 | 32-bit Linux |
| freebsd | amd64 | FreeBSD |

Full list: `go tool dist list`

## Why Go?

- **Fast compilation**: Seconds to build
- **Fast execution**: Native binary performance
- **Single binary**: No runtime needed
- **Easy cross-compilation**: Build for all OSes from one machine
- **Simple deployment**: Just copy the binary
- **Standard library**: Everything we need built-in

## Module

This is a Go module:

```go
module github.com/Winds-AI/agent-traversal-file

go 1.21
```

No external dependencies required!

## License

MIT License - see ../LICENSE






