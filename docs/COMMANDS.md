# IATF Commands Reference

Complete guide to all IATF CLI commands and their options.

---

## Core Commands

### `iatf rebuild <file>`

Rebuilds the INDEX for a single IATF file. The tool scans all sections (marked with `{#section-id}` and `{/section-id}`), extracts metadata (@summary, @created, @modified), and generates an auto-indexed INDEX section.

**Usage:**
```bash
iatf rebuild my-doc.iatf
```

**What it does:**
1. Parses the CONTENT section
2. Extracts section boundaries and metadata
3. Generates an INDEX with line numbers and summaries
4. Updates or creates the INDEX section

---

### `iatf rebuild-all <directory>`

Rebuilds the INDEX for all `.iatf` files in a directory recursively.

**Usage:**
```bash
iatf rebuild-all ./docs
```

**What it does:**
1. Finds all `.iatf` files in the directory
2. Runs rebuild on each file
3. Reports results for each file

---

### `iatf watch <file> [--debug]`

Enables watch mode for a file. The tool monitors for changes and automatically rebuilds the INDEX whenever you save the file.

**Usage:**
```bash
iatf watch my-doc.iatf          # Silent mode (default)
iatf watch my-doc.iatf --debug  # Verbose output
```

**What it does:**
1. Starts monitoring the file for changes (250ms polling interval)
2. Validates file before rebuilding (skips rebuild if invalid)
3. Uses 3-second debounce to handle rapid edits
4. Automatically runs rebuild only if valid
5. Runs in the foreground (press Ctrl+C to stop)

**Silent mode (default):**
- Only prints the filename being watched
- Useful for background monitoring

**Debug mode (--debug):**
- Shows change detection timestamps
- Displays validation errors and rebuild status
- Useful for troubleshooting

**Best for:** Writing and maintaining large documents without manually rebuilding. Debounce prevents unnecessary rebuilds during rapid editing.

---

### `iatf watch-dir <dir> [--debug]`

Watches all `.iatf` files in a directory tree. The tool monitors for changes to any `.iatf` file and automatically rebuilds with per-file debouncing.

**Usage:**
```bash
iatf watch-dir ./docs           # Silent mode (default)
iatf watch-dir ./docs --debug   # Verbose output
iatf watch-dir .                # Current directory
```

**What it does:**
1. Scans the directory tree for all `.iatf` files
2. Prints list of watched files
3. Monitors each file independently (250ms polling interval)
4. Validates and rebuilds each file on changes
5. Detects new `.iatf` files automatically
6. Detects and removes deleted files from watch list
7. Uses 3-second per-file debounce

**Silent mode (default):**
- Only prints the initial list of watched files
- Useful for continuous monitoring

**Debug mode (--debug):**
- Shows per-file change timestamps
- Reports new files, deleted files, and validation errors
- Useful for monitoring multiple files

**Best for:** Monitoring entire project directories during active development. Each file is debounced independently, so changes to multiple files don't interfere.

---

### `iatf unwatch <file>`

Stops watching a file.

**Usage:**
```bash
iatf unwatch my-doc.iatf
```

**What it does:**
1. Removes the file from the watch list
2. No more automatic rebuilds

---

### `iatf watch --list`

Shows all currently watched files.

**Usage:**
```bash
iatf watch --list
```

**What it does:**
1. Lists all files currently being monitored
2. Shows no output if nothing is being watched

---

### `iatf validate <file>`

Validates an IATF file for structural errors, missing metadata, and invalid syntax.

**Usage:**
```bash
iatf validate my-doc.iatf
```

**What it does:**
1. Checks file structure (===INDEX=== and ===CONTENT=== sections)
2. Validates all section metadata (missing @summary, @created, @modified)
3. Checks for malformed section tags
4. Reports errors and warnings
5. Returns exit code 0 if valid, 1 if errors found

---

## Daemon Commands

The daemon enables system-wide file watching. Configure watched paths in `~/.iatf/daemon.json` and start the daemon to monitor all files automatically.

### Configuration

Create `~/.iatf/daemon.json`:

```json
{
    "watch_paths": [
        "/home/user/projects",
        "/home/user/Documents/specs"
    ]
}
```

Update the file to add/remove paths. No restart needed - daemon detects changes.

---

### `iatf daemon start [--debug]`

Starts the system-wide daemon in the background.

**Usage:**
```bash
iatf daemon start          # Silent mode (default)
iatf daemon start --debug  # Verbose output to log
```

**What it does:**
1. Checks if daemon is already running
2. Loads configuration from `~/.iatf/daemon.json`
3. Starts a detached background process
4. Watches all configured paths
5. Logs to `~/.iatf/daemon.log`

**Before running:** Configure `~/.iatf/daemon.json` with paths to watch.

**Debug mode:** Verbose logging to `~/.iatf/daemon.log` includes timestamps and validation details.

---

### `iatf daemon stop`

Stops the running daemon.

**Usage:**
```bash
iatf daemon stop
```

**What it does:**
1. Finds the running daemon by PID
2. Sends SIGTERM signal
3. Cleans up PID file

---

### `iatf daemon status`

Shows daemon status, configured watch paths, and OS service status.

**Usage:**
```bash
iatf daemon status
```

**Output includes:**
1. Running status and PID (if running)
2. All configured watch paths
3. OS service installation status (systemd/launchd/schtasks)

**Example:**
```
Daemon: running (PID 12345)

Watch paths (2):
  /home/user/projects
  /home/user/Documents/specs

OS Service: installed (systemd)
```

---

### `iatf daemon install`

Installs the daemon as an OS service for auto-start on boot/login.

**Usage:**
```bash
iatf daemon install
```

**What it does:**
- **Linux:** Creates systemd user service (`~/.config/systemd/user/iatf-daemon.service`)
- **macOS:** Creates launchd agent (`~/Library/LaunchAgents/com.iatf.daemon.plist`)
- **Windows:** Creates scheduled task (`IATF Daemon` at logon)

**To start the service immediately:**
- Linux: `systemctl --user start iatf-daemon`
- macOS: `launchctl start com.iatf.daemon`
- Windows: `schtasks /run /tn "IATF Daemon"`

---

### `iatf daemon uninstall`

Removes the daemon OS service.

**Usage:**
```bash
iatf daemon uninstall
```

**What it does:**
1. Stops the running service (if any)
2. Disables auto-start
3. Removes the service configuration

---

### `iatf --help`

Shows help information for the CLI.

**Usage:**
```bash
iatf --help
```

---

### `iatf --version`

Shows the current version of IATF.

**Usage:**
```bash
iatf --version
```

---

## Workflow Examples

### Single File Editing

1. Create `my-doc.iatf` with content sections
2. Run `iatf rebuild my-doc.iatf` to generate the INDEX
3. Open the file and verify the INDEX looks correct
4. Edit and save - run rebuild again when done

### Continuous Development (Single File)

1. Create `my-doc.iatf`
2. Start watch mode: `iatf watch my-doc.iatf`
3. Edit the file in your editor
4. Each save automatically rebuilds the INDEX (with validation)
5. Press Ctrl+C when finished

**With debug output:**
```bash
iatf watch my-doc.iatf --debug
# Shows: Change detected → Validation → Rebuild status
```

### Project Documentation (Multiple Files)

**Option 1: Watch directory tree**
```bash
iatf watch-dir ./docs
# Watches all .iatf files, automatically detects new files
```

**Option 2: System-wide daemon**
1. Configure `~/.iatf/daemon.json`:
   ```json
   {
       "watch_paths": [
           "/home/user/projects",
           "/home/user/Documents/specs"
       ]
   }
   ```
2. Start daemon: `iatf daemon start`
3. Daemon monitors all paths automatically
4. Check status: `iatf daemon status`
5. Stop when done: `iatf daemon stop`

**Install as auto-start service:**
```bash
iatf daemon install          # Install for auto-start on boot/login
iatf daemon status           # Verify installation
```

### Manual Bulk Operations

1. Create multiple `.iatf` files in `docs/` folder
2. Run `iatf rebuild-all ./docs` to rebuild all at once
3. Use validate to check everything: `iatf validate docs/*.iatf`

---

## Common Patterns

### Adding a New Section

1. Open your `.iatf` file
2. Add a new section block in CONTENT:
   ```
   {#my-section}
   @summary: Brief description
   @created: 2025-01-20
   @modified: 2025-01-20
   # Section Title

   Content here...
   {/my-section}
   ```
3. Save the file (if watch mode is on, INDEX updates automatically)
4. Otherwise run: `iatf rebuild filename.iatf`

### Linking Between Sections

Reference another section using the `{@section-id}` syntax:

```
See {@my-section} for more details.
```

### Checking Before Publishing

Run validate before sharing your documentation:

```bash
iatf validate my-doc.iatf
```

This ensures all sections have proper metadata and correct formatting.

---

