## Frontend Development Workflow

### 1. API Discovery
- Use `openapi_searchEndpoints` to get API structure from OpenAPI spec
- **Mandatory:** Call the real APIs using curl after `source .agent/api-env.sh` (see `.agent/API_SCRIPT_USAGE_GUIDE.md`) for any API-backed feature
- Capture exact response structures (fields, keys, sample values) to drive UI/forms/state
- Document any discrepancies between spec and runtime behavior

### 2. Context Gathering
- **Mandatory: Read `docs/PROJECT_PATTERNS.md`** for project-wide patterns (uploads, forms, state, routing, etc.)
- Read project structure from AGENTS.md and user's task
- Traverse codebase to understand structure, patterns, and conventions
- Ask clarifying questions before proceeding—don't assume requirements

### 3. Planning
- Use `sequential_thinking` for complex logic
- Propose plan using template at `.agent/PLAN_TEMPLATE.md`
- **Mandatory:** Write the plan to a markdown file named `PLAN_<feature>.md` in `.agent/` (e.g., `.agent/PLAN_certificate-management.md`) before requesting approval
- **Wait for user approval before coding**
- **Explicit user instruction to proceed counts as approval** (e.g., “go ahead and implement”)

### 4. Implementation
- Write production-ready code following existing patterns
- Keep changes focused and incremental

### 5. Testing (if requested)
- Use `.agent/skills/agent-browser` skill for e2e testing
- Skip if not mentioned in task

### 6. Summary
- Provide concise summary of changes made

---

## Bug/Issue Resolution Workflow

### 1. Issue Discovery
- Use `redmine_getIssue` to fetch issue details when user references a bug/issue ID
- Combine: issue description + user context + codebase investigation

### 2. Root Cause Analysis
- Use `sequential_thinking` for complex or unclear issues
- Search web if issue seems unusual—other devs may have documented fixes
- Trace through relevant code paths to pinpoint the problem

### 3. Resolution
- **If user says "report back":** propose fix plan and wait for approval
- **Otherwise:** implement fix directly and provide summary

### 4. Summary
- Explain root cause, what was changed, and why

---

**Principles:**
- Ask before assuming—human makes decisions
- Propose, don't execute, until approved
- Surface important tradeoffs and edge cases
