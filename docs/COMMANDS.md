# IATF Commands

Concise command reference for current CLI behavior.

## Installation & Setup

Quick install commands are in `README.md` and `docs/QUICKSTART.md`.

Build from source:

```bash
cd go
go build -o ../iatf .
```

## Core Commands

### `iatf rebuild <file> [--strict]`

Regenerates INDEX from CONTENT for one file.

Behavior notes:
- Rebuild runs from CONTENT first (it does not require an already-valid INDEX).
- After writing INDEX, the file is validated and rebuild exits non-zero if validation errors remain.
- `--strict` enables fail-fast mode: validate first, and abort rebuild if the file is already invalid.

```bash
iatf rebuild my-doc.iatf
iatf rebuild my-doc.iatf --strict
```

### `iatf rebuild-all <directory>`

Recursively rebuilds all `.iatf` files.

Each file is rebuilt from CONTENT first, then validated. Files that remain invalid are reported as failures.

```bash
iatf rebuild-all ./docs
```

### `iatf validate <file>`

Validates structure, section syntax, annotations, references, and INDEX/CONTENT consistency.

```bash
iatf validate my-doc.iatf
```

Exit code:
- `0`: valid (may include warnings)
- `1`: invalid

### `iatf index <file> [--with-dates]`

Prints INDEX entries in ID-first format:

```text
- section-id {lines:start-end | words:count}
Summary text
```

With `--with-dates`, also prints generated timestamp and per-section `Created/Modified`.

```bash
iatf index my-doc.iatf
iatf index my-doc.iatf --with-dates
```

### `iatf find <file> <query>`

Ranks section IDs using ID + summary matching.

```bash
iatf find my-doc.iatf "rollback incident"
```

Output format:

```text
section-id    (score:N)    summary text
```

### `iatf read <file> <section-id>`

Prints one section body by ID (wrapper tags removed).

```bash
iatf read my-doc.iatf rollback
```

### `iatf read-many <file> <section-id> [section-id...]`

Prints multiple section bodies in requested order.

```bash
iatf read-many my-doc.iatf detect rollback postmortem
```

Output includes markers:

```text
@section: detect
...body...

@section: rollback
...body...
```

If any ID is missing, command fails and prints missing IDs.

### `iatf graph <file> [--show-incoming]`

Shows reference graph from CONTENT (`{@section-id}`).

```bash
iatf graph my-doc.iatf
iatf graph my-doc.iatf --show-incoming
```

Default output:

```text
a -> b, c
d
```

Incoming mode:

```text
b <- a, x
c <- a
```

Notes:
- References inside fenced code blocks are ignored.
- INDEX is not required for `graph`.

## Watch Commands

### `iatf watch <file> [--debug]`

Watches one file and rebuilds after debounce on save.

Watch mode rebuilds first, then validates. In `--debug`, post-rebuild validation failures are printed.

```bash
iatf watch my-doc.iatf
iatf watch my-doc.iatf --debug
```

### `iatf watch-dir <dir> [--debug]`

Watches all `.iatf` files under a directory tree.

Directory watch follows the same rebuild-then-validate flow used by `watch`.

```bash
iatf watch-dir ./docs
iatf watch-dir ./docs --debug
```

### `iatf unwatch <file>`

Stops watching a file.

```bash
iatf unwatch my-doc.iatf
```

### `iatf watch --list`

Lists watched files, or prints `No files are being watched`.

```bash
iatf watch --list
```

## Daemon Commands

Daemon reads watch paths from `~/.iatf/daemon.json`.

```json
{
  "watch_paths": ["/home/user/projects"]
}
```

### Commands

```bash
iatf daemon start [--debug]
iatf daemon stop
iatf daemon status
iatf daemon run [--debug]
iatf daemon install
iatf daemon uninstall
```

## Common Flows

Single-file authoring:

```bash
iatf rebuild my-doc.iatf
iatf validate my-doc.iatf
iatf index my-doc.iatf
iatf find my-doc.iatf "topic"
iatf read my-doc.iatf section-id
```

Multi-section retrieval:

```bash
ids=$(iatf find my-doc.iatf "incident rollback" | cut -f1)
iatf read-many my-doc.iatf $ids
```

## Help

```bash
iatf --help
iatf --version
```
