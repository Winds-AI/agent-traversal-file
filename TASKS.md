# Task List

## Task 1: Verify hash parsing in Go implementation

**Priority:** High  
**Status:** Complete

### Description
Verify that the Go implementation correctly parses `@hash:` annotation from ATF section headers. If parsing is missing, add it and write tests.

### References
- Python implementation: `python/atf.py:82-94` - parses `@hash:`
- Go implementation: `go/main.go:182-184` - already parses `@hash:`
- Spec: `SPECIFICATION.md:212` - `@hash:` reserved annotation
- Implementation gaps: `SPEC_IMPLEMENTATION_INCONSISTENCIES.md:182-192`

### Requirements
1. Verify Go parsing of `@hash:` in `parseContentSection()` function
2. Verify Go updates `@hash` in `updateContentMetadata()` function
3. Add unit tests for hash parsing and update workflow
4. Ensure Python and Go produce identical output for hash

### Test Files
- `examples/simple.atf` - contains `@hash:` annotations

---

## Task 2: Remove @x- custom prefix documentation

**Priority:** High  
**Status:** Complete

### Description
Remove all documentation mentioning `@x-` prefix for custom metadata tags from all markdown files. The project does not support user-defined tags.

### Files to Update
| File | Line(s) | Content to Remove |
|------|---------|-------------------|
| `SPECIFICATION.md` | 95-99 | "Custom fields are allowed with `@x-` prefix" block |
| `SPECIFICATION.md` | 211 | `@x-custom: Custom metadata` example |
| `SPECIFICATION.md` | 224 | "`@x-*` - Custom metadata (preserved but not processed)" |

### Requirements
1. Remove `@x-` prefix documentation from `SPECIFICATION.md`
2. Keep `@hash:` reserved annotation (it's a system tag, not user-defined)
3. Do not modify implementation code (it already ignores unknown tags)

### Related
- Code already ignores user-defined tags: `python/atf.py:82-94` only parses known annotations

---

## Task 3: Add index and read commands for agent-efficient navigation

**Priority:** High
**Status:** Complete

### Description
Add new CLI commands to enable agents to read only the INDEX section and jump directly to specific sections without parsing the entire file.

### Current Commands (python/atf.py:786-813)
| Command | Purpose |
|---------|---------|----------|
| `rebuild` | Rebuild index for file |
| `rebuild-all` | Rebuild all ATF files |
| `watch` | Auto-rebuild on changes |
| `unwatch` | Stop watching file |
| `validate` | Check file validity |

### Proposed Commands

#### `atf index <file>`
**Purpose:** Output only the INDEX section

**Usage:**
```bash
$ atf index doc.atf
# Output: Lines from ===INDEX=== to ===CONTENT=== (the index only)
```

**Implementation:**
1. Find `===INDEX===` delimiter
2. Find `===CONTENT===` delimiter
3. Output lines between them (exclusive)

**Benefits:** Agent reads ~6 lines instead of entire file (for large docs)

#### `atf read <file> <section-id>`
**Purpose:** Extract content for a specific section by ID

**Usage:**
```bash
$ atf read doc.atf intro
# Output: Lines 22-45 (the {#intro} block content)

$ atf read doc.atf auth-keys
# Output: Lines 50-80 (the {#auth-keys} block)
```

**Implementation:**
1. Read INDEX section
2. Parse line range from `{#section-id | lines:start-end}`
3. Output that specific line range from CONTENT section

#### `atf read <file> --title "Title"`
**Purpose:** Extract content by title match

**Usage:**
```bash
$ atf read doc.atf --title "Introduction"
# Output: Lines for section with title "Introduction"
```

**Implementation:**
1. Read INDEX section
2. Find entry matching title (fuzzy match)
3. Read that section's line range

### Requirements
1. Add `index` command to `python/atf.py` and `go/main.go`
2. Add `read` command with `--id` and `--title` options to both implementations
3. Commands should not modify files (read-only)
4. Output should be clean text (no logging, no progress bars)
5. Exit codes: 0=success, 1=not found, 2=error

### Example Workflow for Agents
```bash
# Phase 1: Agent discovers document structure
$ atf index doc.atf
# Returns: 6 lines (index only)

# Phase 2: Agent finds relevant section
$ atf read doc.atf --title "Authentication"
# Returns: 25 lines (specific section content)

# Phase 3: Agent can now work with section directly
# No need to parse entire file
```

### References
- Current command structure: `python/atf.py:770-823`
- Delimiter-based parsing: `SPECIFICATION.md:59-79`
- Index entry format: `SPECIFICATION.md:121-125`

### Files to Modify
- `python/atf.py` - Add `index` and `read` commands
- `go/main.go` - Add `index` and `read` commands

---

## Task 4: Add PID-based warning for rebuild on watched files

**Priority:** Medium
**Status:** Pending

### Description
Prevent redundant rebuilds when a file is being watched and someone manually runs `atf rebuild` on the same file. Currently, this causes the file to be rebuilt twice (manual + auto-trigger from watch).

### Problem
When `atf watch <file>` is running:
1. User runs `atf rebuild <file>` manually
2. Manual rebuild modifies the file
3. Watch detects the file change (checks every 1 second)
4. Watch triggers another rebuild automatically
5. Result: File gets rebuilt twice

### Solution: PID-based warning

**Implementation:**
1. Watch command stores its PID in watch state file (`~/.atf/watch.json`)
2. Rebuild command checks if target file is being watched
3. If watched process is still running (check PID), show warning:
   ```
   Warning: File is being watched (PID 12345)
   Manual rebuild will trigger auto-rebuild.
   Continue anyway? [y/N]:
   ```
4. User can choose to:
   - Press `N` (default) - cancel manual rebuild
   - Press `y` - proceed with rebuild (double rebuild will occur)
   - Run `atf unwatch <file>` first, then rebuild

### Requirements

1. **Modify watch state format** (`~/.atf/watch.json`):
   ```json
   {
     "/path/to/file.atf": {
       "started": "2025-01-20T10:30:00",
       "last_modified": 1234567890.123,
       "pid": 12345
     }
   }
   ```

2. **Update `watch_command()`** (Python & Go):
   - Store current process PID in watch state
   - Clean up PID on exit (normal or Ctrl+C)

3. **Update `rebuild_command()`** (Python & Go):
   - Check if file is in watch state
   - Verify PID is still running (`os.kill(pid, 0)` in Python, `syscall.Kill()` in Go)
   - If running, prompt user for confirmation
   - If user cancels, exit with code 0
   - If user confirms or not watched, proceed with rebuild

4. **Handle stale PIDs**:
   - If PID in watch state is not running, ignore (process died)
   - Optionally clean up stale entries

### Files to Modify
- `python/atf.py`:
  - `watch_command()` - lines 429-494 - add PID storage
  - `rebuild_command()` - lines 378-396 - add PID check and warning
- `go/main.go`:
  - `watchCommand()` - add PID storage
  - `rebuildCommand()` - add PID check and warning

### Implementation Details

**Python PID check:**
```python
import os
import sys

def is_process_running(pid):
    """Check if process with PID is running"""
    try:
        os.kill(pid, 0)  # Signal 0 checks existence without killing
        return True
    except OSError:
        return False

def check_if_watched(filepath):
    """Check if file is being watched and warn user"""
    if not WATCH_STATE_FILE.exists():
        return True  # Not watched, proceed

    watch_state = json.loads(WATCH_STATE_FILE.read_text())
    path_str = str(Path(filepath).resolve())

    if path_str not in watch_state:
        return True  # Not watched, proceed

    pid = watch_state[path_str].get('pid')
    if not pid or not is_process_running(pid):
        return True  # Process not running, proceed

    # File is being watched by running process
    print(f"Warning: File is being watched (PID {pid})")
    print("Manual rebuild will trigger auto-rebuild.")
    response = input("Continue anyway? [y/N]: ").strip().lower()

    return response == 'y'
```

**Go PID check:**
```go
import "syscall"

func isProcessRunning(pid int) bool {
    process, err := os.FindProcess(pid)
    if err != nil {
        return false
    }
    err = process.Signal(syscall.Signal(0))
    return err == nil
}
```

### Testing

1. **Test normal flow:**
   ```bash
   atf watch file.atf &
   atf rebuild file.atf
   # Expected: Warning shown, prompts for confirmation
   ```

2. **Test with dead process:**
   ```bash
   atf watch file.atf &
   PID=$!
   kill $PID
   atf rebuild file.atf
   # Expected: No warning, proceeds normally
   ```

3. **Test unwatch cleanup:**
   ```bash
   atf watch file.atf &
   atf unwatch file.atf
   atf rebuild file.atf
   # Expected: No warning, proceeds normally
   ```

### Benefits
- Prevents accidental double rebuilds
- Educates users about watch/rebuild interaction
- No breaking changes (just adds a confirmation prompt)
- Minimal performance impact (single file read + PID check)

### Alternative Considered
Lock file approach - more complex, risk of orphaned locks
