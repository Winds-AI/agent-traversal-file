---
name: api-plan
description: Creates detailed API integration plans for frontend projects. Use after API discovery when user wants to integrate an API, add new feature, or update existing API integration. Analyzes codebase patterns and creates implementation plan with test cases.
allowed-tools: Read, Grep, Glob, Bash(git:*)
argument-hint: [task-description]
---
# API Integration Planning

Create comprehensive integration plans for API-related frontend tasks. This skill analyzes the codebase, determines if it's a new or existing integration, and produces a detailed implementation plan.

## Prerequisites

Before using this skill:

1. Run `/api-discover` to validate APIs are working
2. Have the API schema/response structure documented
3. Understand the user's task requirements

## Workflow

### Step 1: Determine Integration Type

**New API Integration:**

- No existing code references this endpoint
- Need to design full flow from scratch
- Consider: services, hooks, components, types, error handling, loadings, context handling, cache handling

**API Update/Change:**

- Existing code uses this endpoint
- Need to identify what changes
- Plan cleanup of old code and migration to new structure

Search for existing usage:

```
Grep for endpoint path in src/
Grep for related type definitions
Grep for service/hook files related to this feature
```

### Step 2: Analyze Codebase Patterns

Understand the project's conventions by examining:

**1. Service Layer Pattern**

```
Look in: src/services/, src/api/, src/lib/api/
Check: How are API calls structured? Axios? Fetch? React Query?
```

**2. State Management**

```
Look in: src/hooks/, src/store/, src/context/
Check: Custom hooks? Redux? Zustand? React Query?
```

**3. Type Definitions**

```
Look in: src/types/, src/interfaces/, alongside components
Check: How are API response types defined?
```

**4. Error Handling**

```
Look in: Existing API calls, error boundaries, toast notifications
Check: How are errors displayed? Toast? Modal? Inline?
```

**5. Loading States**

```
Look in: Existing components with data fetching
Check: Skeletons? Spinners? Loading text?
```

**6. UI Patterns**

```
Look in: src/components/
Check: Design system used? Component structure? Styling approach?
```

### Step 3: Check for IATF Spec Files

If AGENTS.md mentions IATF files for business rules:

```
Glob for *.iatf files in project
Read relevant sections for business logic requirements
```

IATF files contain indexed business rules that MUST be followed during integration.

### Step 4: Create Integration Plan

Structure the plan as follows:

```markdown
# API Integration Plan: [Feature Name]

## Overview
- Task: [What user requested]
- Type: [New Integration / API Update]
- APIs Involved: [List endpoints]

## Current State Analysis
[What exists now, if anything]

## Proposed Changes

### 1. Type Definitions
- File: src/types/[feature].ts
- Changes: [New types to add or modify]

### 2. Service/API Layer
- File: src/services/[feature].ts
- Changes: [API call functions to add/modify]

### 3. Custom Hooks (if applicable)
- File: src/hooks/use[Feature].ts
- Changes: [Hook implementation details]

### 4. Components
- Files affected: [List]
- New components: [List if any]
- Changes: [UI modifications]

### 5. Error Handling
- Approach: [How errors will be handled]
- User feedback: [Toast/Modal/Inline]

### 6. Loading States
- Approach: [Skeleton/Spinner/etc]
- Components affected: [List]

### 7. Cleanup (for updates only)
- Files to modify: [List]
- Code to remove: [Describe deprecated code]
- Migration steps: [If data migration needed]

## Test Cases

### Happy Path
1. [Test case 1 - expected flow]
2. [Test case 2 - variations]

### Error Cases
1. [Network error handling]
2. [API error responses (400, 401, 404, 500)]
3. [Validation errors]

### Edge Cases
1. [Empty data]
2. [Large data sets]
3. [Concurrent operations]

## Implementation Order
1. [First step]
2. [Second step]
...

## Files to Create/Modify
| File | Action | Description |
|------|--------|-------------|
| ... | Create/Modify/Delete | ... |

## Dependencies
- [Any libraries to install]
- [Any other tasks that must complete first]

## Risks & Considerations
- [Potential issues]
- [Breaking changes]
- [Performance considerations]
```

### Step 5: Present for Approval

After creating the plan:

1. Present the complete plan to the user
2. Highlight any decisions that need user input
3. Wait for explicit approval before implementation
4. If user requests changes, update the plan accordingly

## Important Guidelines

- **Never start implementation without plan approval**
- **Follow existing codebase patterns** - don't introduce new patterns unless discussed
- **Keep changes minimal** - only change what's necessary for the task
- **Include test cases** - every plan must have testable scenarios
- **Consider backwards compatibility** for API updates and ask user wheather to consider it or not.
- **CRITICAL: Update IATF files** if business rules change (when applicable)

## Using Additional Tools

For complex planning decisions, use:

- **Sequential Thinking MCP** - For multi-branch decision analysis
- **Context7 MCP** - For library documentation (React Query, etc.)
- **Web Search** - For common patterns or error solutions

## Example Plan Header

```markdown
# API Integration Plan: User Discounts Management

## Overview
- Task: Add ability to create, edit, and delete discount codes
- Type: New Integration
- APIs Involved:
  - GET /bandar-admin/discounts (list)
  - POST /bandar-admin/discounts (create)
  - PUT /bandar-admin/discounts/:id (update)
  - DELETE /bandar-admin/discounts/:id (delete)
  - PATCH /bandar-admin/discounts/:id/status (toggle)

## Current State Analysis
No existing discount management in the frontend. Will create new feature module.
...
```
