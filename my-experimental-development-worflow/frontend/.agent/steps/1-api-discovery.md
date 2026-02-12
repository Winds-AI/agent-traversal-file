# Step 1: API Discovery

## Procedure

1. Search `openapi_searchEndpoints` for endpoints matching the feature keywords.
   - Run one broad query first (usually singular), e.g. `certificate`.
   - Re-search only if 0 matches or a specific endpoint is missing.
   - Report endpoints as `(METHOD, PATH)` rows; do not paste long raw tool output.
   - For each endpoint, explicitly list parameter *locations*: `path`, `query`, `body`.
   - If OpenAPI defines no query params for an endpoint, do not assume “extra” query params exist.
2. Scan `src/api/` for existing service files that overlap or need updating.
3. Scan `src/api/routes.ts` for existing route constants.

## Output

```
## API Discovery Report: <Feature>

### Endpoints Found

| # | Method | Path | Description | Status |
|---|--------|------|-------------|--------|
| 1 | GET | /path | ... | New / Existing / Updated |

### Endpoint Details

#### 1. METHOD /path
- Request: params/body shape (include param *location*)
- Response: response shape
- Notes: discrepancies, name changes, deprecations

### Existing Codebase References
- Files integrating related APIs: [list]
- Route constants defined: [list]

### Risk Notes
- [workaround or mismatch to double-check later]
```

## Boundaries

- Do NOT call APIs (Step 2).
- Do NOT plan or implement.
