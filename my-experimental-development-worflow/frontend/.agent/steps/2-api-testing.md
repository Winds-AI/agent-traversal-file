# Step 2: API Testing

## Prerequisites

Step 1 output must exist. If missing, ask user whether to run Step 1 first.

## Goal

Validate behavior (spec drift + parameter acceptance), not just status codes.

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
2. For each endpoint, validate the happy path and 1 contract edge:
   ```bash
   # curl wrapper reads defaults from .agent/scripts/config.toml (locked: no per-call overrides)
   curl "/<path>"
   ```
3. Record: HTTP status, response structure, field names/types.
4. Compare against OpenAPI spec from Step 1.
5. Contract edge checks (pick the most relevant per endpoint):
   - Missing required field (expect 400) or unknown field/param (confirm reject vs ignore).
   - If OpenAPI defines no query params, treat any “extra” query params as suspicious and raise a question in Step 3.
6. If blocked by `API_MODE` (e.g., DELETE), document as unvalidated and raise a question (do not bypass).

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

### Contract Questions Raised
- [e.g., backend rejects unknown query params; should we remove them from frontend?]
```

## Boundaries

- Do NOT plan or implement.
