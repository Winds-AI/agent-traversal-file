# Step 6: Bug / Issue Resolution

## Procedure

1. Get issue details:
   - ID provided → fetch via `redmine_getIssue`.
   - Title/description provided → use directly.
2. Search codebase for related code paths.
3. If API-related: `source .agent/scripts/api-env.sh` and call the endpoint.
4. If framework/library-related: search web.
5. Identify root cause. Apply minimal fix.

## Output

```
## Bug Resolution: <Issue ID/Title>

### Root Cause
- [explanation]

### Fix Applied
- File: path — what changed

### Verification
- [manual steps or suggest Step 5]
```

## Boundaries

- Fix only the specific issue. No refactoring, no unrelated changes.
