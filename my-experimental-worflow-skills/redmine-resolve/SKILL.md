---
name: redmine-resolve
description: Resolves Redmine bug tickets by fetching issue details, analyzing the problem, and guiding through the fix. Use when user provides a Redmine issue ID or mentions fixing a bug from Redmine.
allowed-tools: Read, Grep, Glob, Bash(git:*)
argument-hint: [issue-id]
---

# Redmine Issue Resolution

Fetches Redmine issue details using the `issue.get` MCP tool and guides through resolving the bug/task.

## Workflow

### Step 1: Fetch Issue Details

Use the `issue.get` MCP tool to retrieve the issue:

```
Call MCP tool: issue.get
Input: { "issueId": "$ARGUMENTS" }
```

This returns:
- Issue metadata (ID, status, priority, tracker)
- Subject and description
- Custom fields (Severity, Screen Name, Testing Environment)
- Attached images (as base64 WebP)
- Other attachments

### Step 2: Analyze the Issue

Review the fetched data:

1. **Read the description carefully** - understand what's reported
2. **Examine attached images** - screenshots often show the exact problem
3. **Note custom fields:**
   - Severity: Determines urgency
   - Screen Name: Helps locate the affected component
   - Testing Environment: Where the bug was found

4. **Identify key information:**
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Error messages (if any)

### Step 3: Locate Relevant Code

Based on the issue details:

```
# Search by screen/page name
Grep for route paths matching the screen
Glob for component files with related names

# Search by error message
Grep for error text in codebase

# Search by feature keywords
Grep for relevant function/variable names
```

**Common search patterns:**
```
- Screen Name: "User Profile" -> search for "profile", "user-profile"
- Error: "Failed to load" -> grep for the error message
- Feature: "Discount" -> search services/hooks/components
```

### Step 4: Understand the Bug

After locating the code:

1. **Read the relevant files** - understand current implementation
2. **Trace the data flow** - API call -> state -> render
3. **Identify the root cause:**
   - Missing error handling?
   - Incorrect API usage?
   - State management issue?
   - UI rendering bug?
   - Type mismatch?

### Step 5: Check Related APIs (if applicable)

If the bug involves API calls, use `/api-discover` to:
- Verify the API is working correctly
- Check if response schema matches expectations
- Identify any API changes that might have caused the bug

### Step 6: Propose a Fix

Present findings to the user:

```markdown
# Issue Analysis: #[issue-id]

## Summary
- **Subject:** [issue subject]
- **Severity:** [severity]
- **Screen:** [screen name]
- **Reported:** [date]

## Problem Analysis
[What the bug is and why it's happening]

## Root Cause
[Technical explanation of the root cause]

## Affected Files
| File | Relevance |
|------|-----------|
| src/... | [why this file is affected] |

## Proposed Fix

### Option 1: [Primary fix]
[Description of the fix]

```diff
- old code
+ new code
```

### Option 2: [Alternative if applicable]
[Alternative approach]

## Testing
After the fix:
1. [How to verify the fix works]
2. [Edge cases to test]

## Risk Assessment
- Impact: [High/Medium/Low]
- Regression risk: [What else might be affected]
```

### Step 7: Implement (with user approval)

After user approves the fix:

1. Make the code changes
2. Test locally (suggest using `/api-test` if it's a UI fix)
3. Prepare commit with reference to issue ID

**Commit message format:**
```
fix: [brief description]

Fixes Redmine #[issue-id]

[Detailed description of what was fixed and why]
```

### Step 8: Document Resolution

Provide user with:
- Summary of changes made
- Files modified
- How to test the fix
- Any follow-up tasks

## Issue Priority Guidelines

| Severity | Response |
|----------|----------|
| Critical | Immediate attention, may need hotfix |
| High | Priority fix, schedule ASAP |
| Medium | Normal priority, plan in sprint |
| Low | Fix when convenient |

## Common Bug Patterns

### API-Related Bugs
- Missing error handling
- Incorrect endpoint or method
- Response schema mismatch
- Authentication/authorization issues

### UI Bugs
- Conditional rendering issues
- State not updating
- Missing loading/error states
- Style/layout problems

### Data Bugs
- Type mismatches
- Null/undefined handling
- Incorrect data transformation
- Caching issues

## Integration with Other Skills

- **`/api-discover`** - When bug involves API calls
- **`/api-plan`** - When fix requires significant refactoring
- **`/api-test`** - To verify the fix in the browser

## Example

User: "fix redmine issue 24799"

1. Fetch issue: `issue.get({ issueId: "24799" })`
2. Review: "Discount not applying to cart total"
3. Search: Grep for "discount", "cart", "total"
4. Find: `src/services/cart.ts` has calculation bug
5. Propose: Fix discount calculation logic
6. After approval: Implement and test
7. Commit: "fix: correct discount calculation in cart total\n\nFixes Redmine #24799"
