# Quick Start

Get from zero to working index-first retrieval in a few commands.

## 1. Install

See `README.md` for install commands.

## 2. Rebuild and Validate

Use the bundled fixture:

```bash
iatf rebuild examples/incident-playbook.iatf
iatf validate examples/incident-playbook.iatf
```

## 3. Discover and Retrieve

### View index

```bash
iatf index examples/incident-playbook.iatf
```

Example output shape:

```text
- detect {lines:38-47 | words:30}
First-response detection and role assignment
```

### Find relevant section IDs

```bash
iatf find examples/incident-playbook.iatf "rollback incident"
```

### Read one section

```bash
iatf read examples/incident-playbook.iatf rollback
```

### Read many sections in one command

```bash
iatf read-many examples/incident-playbook.iatf detect rollback postmortem
```

### Inspect reference dependencies

```bash
iatf graph examples/incident-playbook.iatf
iatf graph examples/incident-playbook.iatf --show-incoming
```

## 4. Typical Agent Flow

For targeted retrieval:

1. `iatf index` to inspect available IDs and summaries.
2. `iatf find` to rank likely matches.
3. `iatf read` or `iatf read-many` to load only needed sections.
4. `iatf graph` when dependency/impact context matters.

This is usually more consistent than ad-hoc shell parsing when references and section boundaries matter.

## 5. Token Efficiency Notes

Efficiency is workload-dependent.

Current measurements are documented in:
- `docs/reports/agentic-usability-analysis.md`

In short:
- Large sparse retrieval tasks show strong savings.
- Small files with broad reads may have limited savings.

## Next Docs

- `docs/COMMANDS.md` for full CLI reference
- `docs/SPECIFICATION.md` for format rules
- `docs/testing.md` for validation/test expectations
