---
name: api-discover-and-plan
description: Validates API endpoints, analyzes codebase, and generates developer-approved integration plans. Use when integrating new APIs or updating existing ones.
allowed-tools: Bash(api.sh:*), Read, Grep, Glob, Bash(git:*)
argument-hint: [api-endpoint-name] [integration-context]
---

# API Discovery & Planning

Validate the API, analyze where/how to integrate, generate a plan for developer approval.

## Core Principle

**Ask before deciding. Validate before planning.**

---

## Workflow

```
1. Discover API    → Find endpoint in OpenAPI spec
2. Validate API    → Test with live calls
3. Analyze Codebase → Understand patterns
4. Generate Plan   → Use PLAN_TEMPLATE.md
5. Get Approval    → Wait for developer sign-off
```

**Related Files:**
- **PLAN_TEMPLATE.md** - Required plan structure
- **DATA_SAFETY.md** - CRITICAL test data rules

---

## Step 1: Discover API

**MCP Tool:** `openapi_searchEndpoints`

```
Input: { "path": "endpoint-name-or-keyword" }
Returns: Method, path, parameters, request/response schemas
```

---

## Step 2: Validate API

**Script:** `.agent/api.sh`

```bash
.agent/api.sh [METHOD] [PATH] [OPTIONS]
```

### GET Requests
```bash
.agent/api.sh GET /users
.agent/api.sh GET /users -q page=1 -q limit=10
.agent/api.sh GET /users/123
```

### POST Requests
```bash
.agent/api.sh POST /users -j '{"name": "[AGENT-TEST] User", "email": "agent-test@example.com"}'
.agent/api.sh POST /users -j @payload.json
```

### PUT/PATCH Requests
```bash
.agent/api.sh PUT /users/123 -j '{"name": "[AGENT-TEST] Updated"}'
.agent/api.sh PATCH /users/123 -j '{"name": "[AGENT-TEST] Patched"}'
```

### DELETE Requests
```bash
.agent/api.sh DELETE /users/123
```

### Options
```bash
-q key=value     # Query parameter (repeatable)
-j 'JSON'        # JSON body
-j @file.json    # JSON from file
-F key=value     # Multipart form field
-F file=@path    # File upload
-H 'Header: val' # Custom header
--no-pretty      # Disable JSON formatting
```

**CRITICAL:** Follow DATA_SAFETY.md rules for all write operations (POST/PUT/PATCH/DELETE).

### Validate Response

Check each endpoint:

| Check | What to Look For |
|-------|------------------|
| Status | 2xx = success, 4xx = client error, 5xx = server error |
| Schema | Does response match OpenAPI spec? |
| Latency | <500ms fast, 500ms-2s acceptable, >2s slow |
| Errors | Test 400, 401, 404 scenarios |

### Document Findings

```markdown
### GET /users/:id
Status: ✓ Working
Response: { id, name, email, phone, avatar }
Latency: ~800ms
Notes: Avatar can be null
```

---

## Step 3: Analyze Codebase

Search for existing patterns:

```bash
# Service layer
grep -r "axios\|fetch\|apiClient" src/

# State management
grep -r "useQuery\|createSlice\|zustand" src/

# Type definitions
ls src/types/

# Error handling
grep -r "toast\|notification\|alert" src/
```

**Goal:** Understand how similar features are built so your integration is consistent.

---

## Step 4: Generate Plan

Use the structure in **PLAN_TEMPLATE.md**:

1. **Overview** - APIs, file count, scope boundaries
2. **API Validation Report** - Does it work as spec says?
3. **Design Decisions** - Questions for developer
4. **Implementation Plan** - Pseudocode per file
5. **Modified Files** - NEW/MODIFIED/DELETE list
6. **Blockers/Assumptions** - What needs clarification

---

## Step 5: Get Approval

Present plan. Highlight questions. Wait for explicit approval before coding.

---

## When to Ask Questions

### Ask If Genuinely Ambiguous

**Architecture:**
```
[DECISION 1] Component location?
  Found 3 patterns: src/modules/, src/components/, src/pages/
  → Question: Which pattern for this feature?
```

**Business Logic:**
```
[DECISION 2] Validation timing?
  → Question: Validate on blur, submit, or both?
```

**Scope:**
```
[DECISION 3] Old code cleanup?
  → Question: Remove legacy UserProfile.js or separate ticket?
```

### Don't Ask About Obvious Things

- "Should I test the API?" (Yes)
- "Should I handle errors?" (Yes)
- "Should I use consistent code style?" (Yes)

### When No Questions Needed

```markdown
## Design Decisions
No questions - existing patterns are clear:
- Using Redux (consistent with codebase)
- Using toast for errors (app standard)
```

---

## When to Stop and Ask Developer

- API doesn't work or returns errors
- Response format completely different from spec
- Undocumented authentication required
- Latency unusually high (>10s)
- Unclear if behavior is expected or a bug

**Ask:** "Does this API behavior match what you expect?"

---

## Checklist Before Planning

- [ ] API discovered in OpenAPI spec?
- [ ] API tested with live calls?
- [ ] Response matches spec? (Document discrepancies)
- [ ] Latency acceptable?
- [ ] Error responses tested?
- [ ] Codebase patterns identified?
- [ ] Test data uses `[AGENT-TEST]` markers?

---

## Related Skills

- **api-test** - Browser-based testing after implementation
- **redmine-resolve** - Bug fixing from Redmine tickets
