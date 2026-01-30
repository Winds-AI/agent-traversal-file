---
name: api-discover-and-plan
description: Validates API endpoints, analyzes codebase, and generates developer-approved integration plans. Use when integrating new APIs or updating existing ones. Discovers endpoint structure, tests live calls, analyzes patterns, and creates comprehensive plan for developer review.
allowed-tools: Bash(api.sh:*), Read, Grep, Glob, Bash(git:*)
argument-hint: [api-endpoint-name] [integration-context]
---

# API Discovery & Planning

One unified workflow: validate the API exists and works as spec says, analyze where/how to integrate in codebase, generate a developer-approval plan with all decisions and questions.

## Workflow at a Glance

1. **Discover API** - Find endpoint in OpenAPI spec
2. **Validate API** - Test with live calls, document actual behavior
3. **Analyze Codebase** - Understand integration patterns and conventions
4. **Generate Plan** - Create scannable plan with design decisions and questions
5. **Get Approval** - Wait for developer sign-off before coding

## Core Principle

**Ask before deciding. Validate before planning.**

If you're uncertain about:
- API behavior → Test it with live calls (see API_VALIDATION.md)
- Codebase pattern → Ask developer which pattern to follow (see QUESTIONS_FRAMEWORK.md)
- Scope or approach → Document it as a decision point for developer review

## Files to Reference

### Skill Documentation
- **PLAN_TEMPLATE.md** - The exact plan structure and format
- **API_VALIDATION.md** - How to validate APIs using `.agent/api.sh`
- **QUESTIONS_FRAMEWORK.md** - When to ask questions and what to ask
- **DATA_SAFETY.md** - Rules for test data (critical!)

### Project Context (Read First)
- **CLAUDE.md** / **AGENTS.md** - Project structure, conventions, standards

## Step 1: Discover API

**MCP Tool:** `openapi_searchEndpoints`

```
Input: { "path": "[endpoint-name]" }
Returns: Method, parameters, request/response schemas, integration hints
```

## Step 2: Validate API

Use `.agent/api.sh` to test the endpoint with actual data.

**See API_VALIDATION.md for:**
- Live call syntax (GET, POST, PUT, PATCH, DELETE)
- Response validation checklist
- Error handling
- **Data safety rules (CRITICAL - read this!)**

## Step 3: Analyze Codebase

Grep for existing patterns:
- Service layer pattern (axios? fetch? React Query?)
- State management (Redux? Zustand? Context?)
- Type definitions (where are API types?)
- Error handling (toast? modal? inline?)
- Loading states (skeletons? spinners?)

## Step 4: Generate Plan

Use the structure in PLAN_TEMPLATE.md:

**Sections:**
1. Overview - What's being integrated, which files change, scope boundaries
2. API Validation Report - Does the API work as spec says?
3. Design Decisions (with questions) - Explicit choices that need developer input
4. Implementation Plan - Pseudocode of what will be built, file by file
5. Modified Files - Create/modify/delete list
6. Blockers or Assumptions - Anything needing clarification

**Key:** Plan should be scannable in 5-10 minutes. Developer approves → you code.

## Step 5: Get Approval

Present plan to developer. Highlight questions that need answering. Wait for explicit approval.

## Important Notes

- Test APIs BEFORE planning (see API_VALIDATION.md)
- Follow data safety rules when creating test data (see DATA_SAFETY.md)
- If API behavior differs from spec, document the actual behavior
- If you find existing code that needs cleanup, ask developer first
- Plan approval is mandatory before coding starts
