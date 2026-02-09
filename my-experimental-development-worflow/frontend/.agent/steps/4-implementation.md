# Step 4: Implementation

## Prerequisites

Plan must exist at `.agent/plans/PLAN_<feature>.md`. If missing, ask user.

When run with Step 3: skip plan approval, use default answers to decisions.

## Procedure

1. Read the plan.
2. Read `docs/PROJECT_PATTERNS.md` and the reference module identified in the plan.
3. Implement file by file per the plan's pseudocode.
4. Only implement what is in the plan.

## Output

```
## Implementation Summary: <Feature>

### Files Created
- path — description

### Files Modified
- path — what changed

### Notes
- Deviations from plan (if any) and why
```

## Boundaries

- Do NOT run browser tests (Step 5).
- Do NOT discover/test APIs (Steps 1-2).
