# Task List

## Task 1: Add PID-based warning for rebuild on watched files

**Priority:** Medium
**Status:** Completed

### Summary
Prevents redundant double rebuilds when manually running `iatf rebuild` on a file that's being watched.

### What was implemented

**Python (`python/iatf.py`):**
- `is_process_running(pid)` - checks if process exists
- `prompt_user_confirmation()` - interactive yes/no prompt
- `check_watched_file()` - validates PID and prompts user
- `watch_command()` - stores PID, cleans up on exit/signals
- `rebuild_command()` - checks for watched files before rebuild

**Go (`go/main.go` + platform files):**
- `go/process_unix.go` - Unix PID check using `Signal(0)`
- `go/process_windows.go` - Windows PID check using `OpenProcess` API
- `promptUserConfirmation()` - interactive prompt, returns default for non-TTY
- `checkWatchedFile()` - validates PID and prompts user
- `watchCommand()` - stores PID, cleans up on SIGINT/SIGTERM
- `rebuildCommand()` - checks for watched files before rebuild

### Behavior

When rebuilding a watched file:
```
Warning: This file is being watched by another process (PID 12345)
A manual rebuild will trigger an automatic rebuild from the watch process.
This will cause the file to be rebuilt twice.

Options:
  - Press 'y' to proceed with manual rebuild anyway
  - Press 'N' (default) to cancel
  - Run 'iatf unwatch file.iatf' to stop watching first

Continue with manual rebuild? [y/N]:
```

**Exit codes:**
- User cancels â†’ exit 1 with "Rebuild cancelled, no changes made."
- User confirms â†’ proceeds with rebuild
- Non-interactive (CI/scripts) â†’ returns default (cancel)

### Edge cases handled
- Stale PID (process dead) â†’ proceeds without warning
- Corrupt watch state â†’ cleans up and exits watch
- File deleted during watch â†’ cleans up PID
- Windows support â†’ uses `OpenProcess` API instead of Unix signals
- Non-TTY stdin â†’ returns default to avoid hanging in CI

### Documentation
- README.md updated with rebuild warning info
- Watch state file format documented



