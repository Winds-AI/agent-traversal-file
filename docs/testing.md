# Testing Guide

## Goal

Ensure CLI behavior, format rules, and fixtures stay aligned.

## Required Checks

### 1. Go Tests

```bash
cd go
go test ./...
```

### 2. Fixture Validation Matrix

```bash
for f in examples/*.iatf examples/valid/*.iatf examples/warnings/*.iatf; do
  ./iatf validate "$f"
done
for f in examples/invalid/*.iatf; do
  ./iatf validate "$f"
done
```

Expected:
- `examples/` + `examples/valid/`: pass clean
- `examples/warnings/`: pass with warnings
- `examples/invalid/`: fail

### 3. Command Smoke Flow

```bash
./iatf rebuild examples/incident-playbook.iatf
./iatf validate examples/incident-playbook.iatf
./iatf index examples/incident-playbook.iatf
./iatf find examples/incident-playbook.iatf "rollback"
./iatf read examples/incident-playbook.iatf rollback
./iatf read-many examples/incident-playbook.iatf detect rollback
./iatf graph examples/incident-playbook.iatf
./iatf graph examples/incident-playbook.iatf --show-incoming
```

## Watch/Daemon (when touched)

If a change affects watcher or daemon behavior, also test:
- `iatf watch <file>` (silent and `--debug`)
- `iatf watch-dir <dir>` (silent and `--debug`)
- `iatf daemon start|status|stop`
