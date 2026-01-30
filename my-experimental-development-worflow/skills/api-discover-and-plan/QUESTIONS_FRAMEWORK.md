# Questions Framework: When & What to Ask

This document tells you when to ask questions vs. when to just use codebase conventions.

---

## Phase 1: API Validation

**Ask if:** Actual API behavior doesn't match the spec or you're unsure about behavior.

### Questions to Ask

- "API returned field X but OpenAPI says Y. Is this a backend bug or expected?"
- "This endpoint needs authentication header [name]. How should I get the token?"
- "API response sometimes returns null for [field]. Should UI handle this as missing data or error?"
- "Response takes 3-5 seconds. Should I add timeout handling or is that normal?"
- "Pagination uses [cursor/limit/offset]. Is this pattern already used elsewhere in app?"

### Don't Ask

- "Should I test GET requests?" (Obviously yes)
- "Should I document the response?" (Of course)

---

## Phase 2: Planning - Codebase Patterns

**First:** Check if the pattern already exists in codebase. If yes, just use it.

**Only ask if:** Multiple patterns exist or you genuinely can't determine the standard.

### When to Check First (Don't Ask)

Pattern already established:
- Service layer: `src/services/apiClient.ts` handles all API calls → use this pattern
- State management: Codebase uses Redux consistently → ask only if unclear
- Types: Interfaces defined in `src/types/` → follow this structure
- Error handling: All errors shown as toasts → use toasts

### When to Ask

Only if GENUINELY AMBIGUOUS:

**Architecture Decision:**
```
[DECISION 1] Component location for new UserProfile?
  Found: 3 different patterns in codebase:
    - Feature modules: src/modules/[feature]/components/
    - Shared components: src/components/[category]/
    - Page-specific: src/pages/[page]/components/
  → Question: Which pattern fits this feature?
```

**Library Choice:**
```
[DECISION 2] State management for API data?
  Codebase has both Redux (global state) and React Query (component state)
  → Question: Which should I use for user profile data?
```

**Pattern Inconsistency:**
```
[DECISION 3] Error handling?
  Found: Some parts use toast, some use modals
  → Question: What's the standard for errors in forms?
```

### Don't Ask About

- Code style (if linter is configured, it handles this)
- Component naming (follow existing pattern)
- File locations (match existing structure)
- Loading states (check what other components use)

---

## Phase 3: Planning - Business Logic & Scope

**Always ask about scope/business logic.** Developer knows intent, you don't.

### Always Ask These

**Scope:**
- "Should I handle [related feature]? (e.g., should profile update trigger notification?)"
- "Is cleanup of old code [OldComponent.js] in scope or separate ticket?"
- "Should I test this specific scenario [edge case]?"

**Business Rules:**
- "Should validation happen on blur, submit, or both?"
- "On update error, should form reset or keep user input?"
- "Should old avatar be kept if upload fails?"
- "Is this field required if user has no previous value?"

**Integration Points:**
- "This change affects [OtherComponent]. Should I update it too or just handle integration point?"
- "Should I add logging/analytics for this feature?"

---

## Phase 4: During Implementation

**You might discover things that need clarification.**

### Ask If

- Business logic is unclear: "Should X happen before or after Y?"
- Multiple valid approaches exist: "Faster implementation but less maintainable, vs. slower but cleaner. Which?"
- You find related bugs: "Found existing bug in [code]. Fix it now or separate ticket?"
- Scope changed: "Feature requires [new thing] not in plan. In scope?"

### Don't Ask

- "Should I use const or let?" (Codebase style will guide this)
- "Should I test this happy path?" (Obviously yes)

---

## Phase 5: Testing & Reporting

**Report findings. Ask for guidance on next steps.**

### Report Format

```
✓ Feature works in happy path. Tested: [scenarios]
⚠ Feature fails when: [specific condition]
? Found existing bug in [code]. Should I fix while here?
? Performance: API takes X seconds. Acceptable?
```

### Ask If

- "Should I investigate this failure or escalate to QA?"
- "Found this performance issue. Priority or out of scope?"
- "This change affects [other module]. Should I test that too?"

---

## Questions Checklist

### Before Starting Plan

- [ ] API validated and working? If not, ask about discrepancies
- [ ] Codebase pattern identified? If unsure, ask which pattern
- [ ] Scope clear? If not, ask about boundaries
- [ ] Business rules understood? If not, ask for clarification

### In Plan

- [ ] Each ambiguous decision has a question?
- [ ] No questions about obvious things?
- [ ] Questions are answerable (not vague)?
- [ ] Important decisions are highlighted?

### After Developer Approves

- [ ] Do I understand the answer to each question?
- [ ] Can I proceed without more clarification?
- [ ] Are there any new edge cases from the answers?

---

## Example: When to Ask vs. When to Assume

### WRONG: Asking About Obvious Things

```
[DECISION 1] Should I write clean code?
[DECISION 2] Should I handle errors?
[DECISION 3] Should I test my changes?
```

❌ These are given. Don't ask.

### RIGHT: Asking About Ambiguous Things

```
[DECISION 1] Should validation errors show as inline messages or toast notifications?
  Current app uses: Both in different places
  → Question: Standard approach for form validation?

[DECISION 2] Should user profile updates be cached or always fetch fresh?
  → Question: Performance vs. freshness trade-off?

[DECISION 3] Should old avatar be deleted if user uploads new one?
  → Question: Storage/cleanup considerations?
```

✓ These require developer intent/knowledge.

---

## When Everything Is Clear

If you've answered all questions and have no ambiguities:

```
## Design Decisions

No design decisions needed - existing patterns cover this:
- Using Redux (consistent with codebase)
- Using toast for errors (app standard)
- Placing in src/modules/users/ (matches architecture)
```

This is fine. Not every plan needs multiple decisions.
