# Testing Guidelines

## No Automated Test Suite (Yet)

Validate changes by manually running all commands on files in `examples/`:

### Core Commands
1. `rebuild` - Rebuild single file
2. `rebuild-all` - Rebuild directory
3. `validate` - Validate file structure
4. `index` - Extract INDEX section
5. `read` - Read section by ID
6. `graph` - Show reference graph

### Watch Commands
7. `watch <file>` - Watch single file (silent and --debug modes)
8. `watch-dir <dir>` - Watch directory tree (silent and --debug modes)
9. `unwatch <file>` - Stop watching file
10. `watch --list` - List watched files

### Daemon Commands
11. `daemon start` - Start daemon (silent and --debug modes)
12. `daemon stop` - Stop daemon
13. `daemon status` - Show daemon status
14. `daemon install` - Install OS service
15. `daemon uninstall` - Remove OS service

## Testing Approach

Test task requirements by building, running, and validating with the Go CLI.

## Manual Test Plan

### Watch Command Testing
- Test `watch` in silent mode: verify only "Watching:" printed
- Test `watch --debug`: verify verbose output on changes
- Edit watched file: verify 3-second debounce delay
- Make rapid edits: verify debounce resets timer
- Introduce syntax error: verify rebuild skipped (silent unless --debug)
- Fix error: verify rebuild succeeds

### Watch-Dir Command Testing
- Test `watch-dir .`: verify file list printed initially
- Test `watch-dir . --debug`: verify verbose output per file
- Create new .iatf file: verify auto-detected
- Edit multiple files: verify per-file debounce
- Delete file: verify removed from watch list

### Daemon Testing
- Test `daemon start` without config: verify error message with example config
- Configure `~/.iatf/daemon.json`: add test paths
- Test `daemon start`: verify PID file created
- Test `daemon status`: verify running status and paths displayed
- Test `daemon stop`: verify process terminates
- Test `daemon install`/`uninstall`: verify service created/removed

### Cross-Platform Service Testing
- **Linux**: Verify systemd user service in `~/.config/systemd/user/`
- **macOS**: Verify launchd plist in `~/Library/LaunchAgents/`
- **Windows**: Verify scheduled task creation via `schtasks`

## Go Tests

Go tests are noted as TODO. If you add tests, ensure `go test` remains clean.
