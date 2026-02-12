# Step 4: Implementation

## Prerequisites

Plan must exist at `.agent/plans/PLAN_<feature>.md`. If missing, ask user.

When run with Step 3: skip plan approval only if plan has ≤8 files and ≤2 decisions. Otherwise present plan and wait.

## Procedure

1. Read the plan and the reference module identified in it.
2. Read project patterns (see Resources in `Agent.md`).
3. If the plan has a `## Phases` section, execute one phase at a time:
   - Complete all files in the phase.
   - Run lint/build. Fix before moving on.
   - Git commit with phase label.
4. If no phases, implement file by file per the plan.
5. Only implement what is in the plan.

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
