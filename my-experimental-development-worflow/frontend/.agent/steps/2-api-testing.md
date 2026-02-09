# Step 2: API Testing

## Prerequisites

Step 1 output must exist. If missing, ask user whether to run Step 1 first.

## Procedure

1. Run: `source .agent/scripts/api-env.sh`
2. For each endpoint from the discovery report:
   ```bash
   API_TOKEN_NAME=bandar-dev-superuser curl "$API_BASE/<path>"
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
