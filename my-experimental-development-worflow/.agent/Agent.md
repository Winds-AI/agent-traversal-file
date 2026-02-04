## Session Continuity

Use `.agent/HANDOFF.md` to persist context across sessions.

### Session Start
1. Read `.agent/HANDOFF.md` if it exists — respect decisions already made, don't re-ask them
2. If an active plan exists, check `git log` for changes to planned files since approval date — flag staleness to developer if found
3. Mention any paused work so developer can decide to resume or start fresh

### Session End
Update `.agent/HANDOFF.md`:

```markdown
# Session Handoff — [date]

## Current Task
[feature/issue ID + one-line description]

## Status: [planning | implementing | testing | blocked | paused | completed]

## Done
- [x] [completed items]

## Remaining
- [ ] [pending items]

## Active Plan
[path + approval date, or "none"]

## Key Decisions
- [developer decisions — future sessions must not re-ask these]

## Blockers
- [anything blocking or needing attention]

## Paused Work
- [interrupted tasks with context to resume]
```

- Developer may edit HANDOFF.md — trust it over your assumptions
- If HANDOFF.md conflicts with codebase state, ask developer
- When switching tasks, move current task to Paused Work first

---

## Frontend Development Workflow

### 1. API Discovery
- Use `openapi_searchEndpoints` for API structure
- Test with curl after `source .agent/api-env.sh` (see `.agent/API_SCRIPT_USAGE_GUIDE.md`)
- Document discrepancies between spec and runtime

### 2. Context Gathering
- Read project context from Agents.md and user's task
- Traverse codebase to understand patterns and conventions

### 3. Planning
- Use `sequential_thinking` for complex logic
- Propose plan using `.agent/PLAN_TEMPLATE.md`
- **Wait for user approval before coding**

### 4. Implementation
- Follow existing patterns, keep changes focused and incremental

### 5. Testing (if requested)
- Use `.agent/skills/agent-browser` for e2e testing

### 6. Summary
- Summarize changes made
- Update `.agent/HANDOFF.md`

---

## Bug/Issue Resolution Workflow

### 1. Issue Discovery
- Use `redmine_getIssue` for issue details
- Combine: issue description + user context + codebase investigation

### 2. Root Cause Analysis
- Use `sequential_thinking` for complex issues
- Search web if issue seems unusual
- Trace relevant code paths

### 3. Resolution
- **"report back" requested:** propose fix, wait for approval
- **Otherwise:** implement directly

### 4. Summary
- Explain root cause, changes, and why
- Update `.agent/HANDOFF.md`

---

**Principles:**
- Ask before assuming — human makes decisions
- Propose, don't execute, until approved
- Surface tradeoffs and edge cases

---

## Workflow Self-Improvement

When you hit friction during any workflow step, surface a suggestion inline:

> **WORKFLOW SUGGESTION:** [summary] | **Friction:** [what happened, which step] | **Change:** [specific file/tool/skill to modify] | **Impact:** [one line]

**Trigger on:**
- MCP tool missing or insufficient for what you needed
- Workflow step ambiguous or causing unnecessary back-and-forth
- Recurring sub-task that should be a skill or script
- Information scattered across files that should be pre-documented

**Suggest changes to:** `Agent.md`, `Agents.md`, `PLAN_TEMPLATE.md`, `.agent/skills/*`, `.agent/*.sh`, MCP configs

Log inline and continue — don't block. Be specific: "add X to Y", not "improve Z".
