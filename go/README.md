# IATF Tools - Go Implementation

High-performance Go implementation that compiles to standalone binaries.

## Features

- ✅ Single static binary (no dependencies)
- ✅ Cross-compiles to all platforms
- ✅ Fast (~10-50ms rebuild time)
- ✅ Small binary size (~2-5MB)
- ✅ All 15 commands implemented
- ✅ Watch mode with debouncing and validation
- ✅ Directory watching with auto-detection
- ✅ System-wide daemon with OS service integration

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

### Core Commands
```bash
./iatf rebuild document.iatf       # Rebuild single file
./iatf rebuild-all ./docs          # Rebuild all .iatf files
./iatf validate document.iatf      # Validate file structure
```

### Watch Commands
```bash
./iatf watch document.iatf         # Watch single file (silent)
./iatf watch document.iatf --debug # Watch with verbose output
./iatf watch-dir ./docs            # Watch directory tree
./iatf unwatch document.iatf       # Stop watching
./iatf watch --list                # List watched files
```

### Daemon Commands
```bash
./iatf daemon start                # Start system-wide daemon
./iatf daemon start --debug        # Start with verbose logging
./iatf daemon stop                 # Stop daemon
./iatf daemon status               # Show daemon status
./iatf daemon install              # Install as OS service
./iatf daemon uninstall            # Remove OS service
```

## Code Structure

```go
// Types
type Section struct { ... }       // Represents a section
type WatchState map[string]WatchInfo
type WatchInfo struct { ... }
type DaemonConfig struct { ... }  // Daemon configuration
type fileState struct { ... }     // Per-file watch state

// Core Functions
parseContentSection()  // Parse CONTENT section
generateIndex()        // Generate INDEX from sections
rebuildIndex()         // Main rebuild logic
validateFileQuiet()    // Validate without output (returns errors)

// Watch Commands
watchCommand()         // Watch single file with debounce
watchDirCommand()      // Watch directory tree
unwatchCommand()       // Stop watching
processFileForWatch()  // Internal: validate and rebuild

// Daemon Commands
daemonStartCommand()      // Start daemon process
daemonStopCommand()       // Stop running daemon
daemonStatusCommand()     // Show daemon status
daemonRunCommand()        // Internal: daemon main loop
watchMultipleDirs()       // Watch multiple paths simultaneously

// Platform-specific (daemon_unix.go / daemon_windows.go)
daemonInstallCommand()    // Install OS service
daemonUninstallCommand()  // Remove OS service
daemonSysProcAttr()       // Process attributes for detaching
isServiceInstalled()      // Check if service is installed
```

## Dependencies

**Minimal!** Nearly pure Go standard library:

### Standard Library
- `encoding/json` - Config and watch state
- `fmt` - Output
- `io/fs` - Directory walking
- `os` - File operations and signals
- `os/exec` - Daemon process control
- `os/signal` - Signal handling
- `path/filepath` - Path handling
- `regexp` - Pattern matching
- `sort` - Sorting
- `strings` - String operations
- `sync` - Synchronization (mutexes for file state)
- `syscall` - Process signals and attributes
- `time` - Timestamps and debouncing

### External (Windows only)
- `golang.org/x/sys/windows` - Windows process API (daemon service)

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






