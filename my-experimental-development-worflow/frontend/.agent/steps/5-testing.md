# Step 5: Testing

These are **user-flow verifications in a headless browser**, not code-level unit tests.

## Procedure

1. Get test cases from:
   - Plan's `## Test Cases` section (if exists), OR
   - Derive from implementation: cover all happy-path user flows.
2. For each test case, use `agent-browser` skill to:
   - Navigate to the page.
   - Perform the action (click, fill, submit).
   - Verify outcome (element visible, toast shown, data updated).
3. Record: Pass / Fail / Blocked.

## Output

```
## Test Results: <Feature>

| # | Test Case | Result | Notes |
|---|-----------|--------|-------|
| 1 | Load page, verify data | Pass | — |
| 2 | Submit form | Fail | Toast missing |

### Failure Details
#### Test 2
- Expected: Success toast
- Actual: No toast, data saved
```

## Boundaries

- Do NOT modify code. Report issues only.
- Do NOT call APIs via curl.
