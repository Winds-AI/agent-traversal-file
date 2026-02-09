# Step 3: Context Gathering & Plan

## Procedure

### Gather Context

1. Read `docs/PROJECT_PATTERNS.md`.
2. Read `AGENTS.md`.
3. Find the closest existing module to the feature. Read its `src/sections/`, `src/api/`, `src/pages/` files as reference.
4. Check: `src/routes/`, `src/layouts/dashboard/config-navigation.tsx`, `src/constants/permission-modules.ts`.
5. If Step 1/2 output exists, incorporate it. Otherwise mark API validation as pending.

### Write Plan

6. Use template at `.agent/docs/PLAN_TEMPLATE.md`. Required sections:
   - Overview
   - API Validation Report
   - Decisions (only ambiguous ones and important ones that decide flow)
   - Implementation Plan
   - Blockers/Assumptions
7. Add `## Test Cases` only if Step 5 is part of current task.
8. Save to `.agent/plans/PLAN_<feature>.md`.
9. Wait for user approval — unless Step 4 is also in the current task.

## Boundaries

- Do NOT write code.
- Do NOT run browser tests.
