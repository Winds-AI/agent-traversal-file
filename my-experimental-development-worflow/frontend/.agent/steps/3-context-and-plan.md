# Step 3: Context Gathering & Plan

## Procedure

### Gather Context

1. Read project patterns and project structure files (see Resources in `Agent.md`).
2. Find the closest existing module to the feature. Read its pages, API layer, and component files as reference.
   - Do not assume the reference module is correct; note any workarounds/mappings and confirm they match the current feature's API contract.
3. Check route config, navigation config, and permission definitions (paths per project patterns).
4. If Step 1/2 output exists, incorporate it. Otherwise mark API validation as pending.
5. Before finalizing the plan, list the integration-critical open questions (permissions/module key, param locations, mutation semantics, response shape differences). If unanswered, mark explicit assumptions.

### Write Plan

6. Use template at `.agent/docs/PLAN_TEMPLATE.md`. Required sections:
   - Overview
   - API Validation Report
   - Open Questions (must be answered or accepted as assumptions)
   - Decisions (only ambiguous ones and important ones that decide flow)
   - Implementation Plan
   - Blockers/Assumptions
7. Add `## Phases` when plan has >8 files or multiple sub-domains (see template).
8. Add `## Test Cases` only if Step 5 is part of current task.
9. Save to `.agent/plans/PLAN_<feature>.md`.
10. Wait for user approval — unless Step 4 is also in the current task.

## Boundaries

- Do NOT write code.
- Do NOT run browser tests.
