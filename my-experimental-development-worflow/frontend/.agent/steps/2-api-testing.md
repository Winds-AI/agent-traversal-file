# Step 2: API Testing

## Prerequisites

Step 1 output must exist. If missing, ask user whether to run Step 1 first.

## Safe-Updates Rules (Agent-Friendly)

When `API_MODE=safe-updates`, you may call mutating endpoints, but you must keep changes minimal and traceable:

1. Always tag test data with `[agent-test]` in a human-visible field (e.g., `title`, `name`, `description`, `notes`) so it can be found and cleaned up later.
2. Updates must be minimal:
   - Only add/remove the `[agent-test]` marker (or change the smallest required field to exercise the endpoint).
   - Do not overwrite unrelated existing values.
3. Create is allowed:
   - Only create records that are clearly labeled `[agent-test] ...`.
   - Record created IDs in the validation report so cleanup is possible.
4. Deletes/unassigns are NOT allowed in `safe-updates` (by default in this repo’s curl wrapper).
   - If the user explicitly enables `API_MODE=full-access`, you may `DELETE` only what you created/assigned during the current test run.
5. Prefer non-mutating validation where possible:
   - Use invalid payloads/IDs to confirm validation and response shapes when that avoids persistent changes.

## Procedure

1. Run: `source .agent/scripts/api-env.sh`
2. For each endpoint from the discovery report:
   ```bash
   # curl wrapper reads defaults from .agent/scripts/config.toml (locked: no per-call overrides)
   curl "/<path>"
   ```
3. Record: HTTP status, response structure, field names/types.
4. Compare against OpenAPI spec from Step 1.
5. Flag: missing fields, extra fields, type mismatches, unexpected nulls.

## Output

```
## API Validation Report: <Feature>

### Results

| # | Endpoint | Status | Result | Notes |
|---|----------|--------|--------|-------|
| 1 | GET /path | 200 | Pass | — |
| 2 | POST /path | 400 | Warn | Missing field X |

### Response Samples

#### 1. GET /path
- Status: 200
- Response: { field1: type, ... }
- Spec match: Yes/No — details

### Discrepancies
- [list]
```

## Boundaries

- Do NOT plan or implement.
