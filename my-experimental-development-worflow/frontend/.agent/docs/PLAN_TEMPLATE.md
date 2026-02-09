# Plan Template

## 1. Overview

```
## Overview
- APIs: GET /users/:id — fetch profile (new), PUT /users/:id — update profile (new)
- Files: 3 new, 2 modified, 1 deleted
- Out of scope: [items]
```

## 2. API Validation Report

```
## API Validation Report
✓ GET /users/:id — 200, returns { id, name, email, phone, avatar }
⚠ Avatar field sometimes null
? Is null avatar a backend bug or expected?
```

## 3. Decisions

Only genuinely ambiguous ones.

```
## Decisions
[DECISION 1] Component location?
  A: src/modules/users/UserProfile.tsx
  B: src/components/User/Profile.tsx
  → Question: which fits your architecture?
```

## 4. Implementation Plan

Tag each file header: `(NEW)`, `(MODIFIED)`, or `(DELETE)`. This is the file manifest.

```
## Implementation Plan

### src/types/User.ts (NEW)
1. UserProfile interface from API response
2. UserProfileUpdate interface for form

### src/pages/Settings.tsx (MODIFIED)
1. Import UserProfile
2. Add to layout

### src/components/OldUserProfile.js (DELETE)
```

## 5. Blockers/Assumptions

```
## Blockers/Assumptions
- Assuming Bearer token configured
- Need clarification: avatar upload in scope?
- Risk: API latency on initial load
```

---

## Optional: Test Cases

Include only when Step 5 is part of the current task.

```
## Test Cases
- Load page (data renders)
- Create/update flow (success + error)
- Empty state
```
