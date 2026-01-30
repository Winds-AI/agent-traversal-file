# API Discovery & Planning Skill

Consolidated skill for validating APIs and generating developer-approved integration plans.

## File Structure

```
api-discover-and-plan/
├── SKILL.md                    ← Agent instructions (minimal, links to others)
├── PLAN_TEMPLATE.md            ← How plans are structured
├── API_VALIDATION.md           ← How to test APIs with .agent/api.sh
├── DATA_SAFETY.md              ← Critical rules for test data
├── QUESTIONS_FRAMEWORK.md      ← When to ask what questions
└── README.md                   ← This file
```

## Quick Reference

### For Agents

1. Read **SKILL.md** - Your main instructions
2. Validate APIs using **API_VALIDATION.md**
3. Follow test data rules in **DATA_SAFETY.md**
4. Ask questions per **QUESTIONS_FRAMEWORK.md**
5. Generate plan using **PLAN_TEMPLATE.md**

### For Developers

1. Understand plan structure in **PLAN_TEMPLATE.md**
2. Expect questions from **QUESTIONS_FRAMEWORK.md**
3. Review agent's API validation findings
4. Approve plan before agent codes

## Workflow Summary

```
Developer Request
    ↓
Agent: Discover API (MCP: openapi_searchEndpoints)
    ↓
Agent: Validate API (Script: .agent/api.sh)
    ↓
Agent: Analyze Codebase (Grep, Read files)
    ↓
Agent: Generate Plan (Using PLAN_TEMPLATE.md)
    ↓
Developer: Review & Approve
    ↓
Agent: Ready to Code (separate skill: code-integration)
```

## Key Principles

- **Ask before deciding** - Ambiguous? Ask developer.
- **Validate before planning** - Test the API before assuming it works.
- **Protect production data** - Use `[AGENT-TEST]` markers. Never delete without markers.
- **Scannable plans** - 5-10 minute reviews. No fluff.
- **Explicit scope** - What's in, what's out, what's unclear.

## Progressive Disclosure

This skill follows progressive disclosure principles:

- **SKILL.md** - Minimal instructions linking to detailed docs
- **Supporting files** - Detailed guidance only when needed
- **No redundancy** - Each file has one purpose
- **No fluff** - Every line is actionable

## Related Skills

- **code-integration** - Implement the approved plan
- **test-automation** - Browser-based testing
- **bug-fixing** - Fix issues from Redmine

## Changed From

Previously separate skills:
- Old `api-discover` → Merged into SKILL.md + API_VALIDATION.md
- Old `api-plan` → Merged into SKILL.md + PLAN_TEMPLATE.md

Reason: Discovery always leads to planning. Single skill is simpler for developers.
