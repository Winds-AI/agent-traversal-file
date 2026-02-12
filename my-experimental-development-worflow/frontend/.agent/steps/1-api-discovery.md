# Step 1: API Discovery

## Procedure

1. Search `openapi_searchEndpoints` for endpoints matching task.
   - One broad query first; prefer sequential tool calling (singular), e.g. `certificate`.
   - Re-search only if 0 matches or specific endpoint missing.
2. Scan existing API service files for overlap (see project patterns for API layer paths).
3. Scan existing route constants for overlap.

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

- No API calls (Step 2).
- No plan or implementation.
