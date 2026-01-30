# Plan Template

All plans must follow this 6-section structure. Developer should be able to scan and approve in 5-10 minutes.

---

## Required Sections

### 1. Overview

```markdown
## Overview
- APIs being integrated: GET /users/:id, PUT /users/:id
- Files: 3 new, 2 modified, 1 deleted
- Out of scope: User deletion, avatar upload (separate tickets)
```

### 2. API Validation Report

```markdown
## API Validation Report

✓ GET /users/:id works, returns user object as spec says
✓ Response includes: id, name, email, phone, avatar
⚠ API takes 2-3 seconds on first call
⚠ Avatar field sometimes null even when user has avatar
? Question: Is the null avatar a backend bug or expected?
```

### 3. Design Decisions

```markdown
## Design Decisions

[DECISION 1] Component location?
  Option A: New module at src/modules/users/UserProfile.tsx
  Option B: Add to existing src/components/User/Profile.tsx
  → Question: Where fits your architecture?

[DECISION 2] State management?
  Codebase uses Redux for global state
  → Question: Redux or React Query for this feature?

[DECISION 3] Legacy code cleanup?
  → Question: Remove old UserProfile.js or separate ticket?
```

Only include decisions that are genuinely ambiguous.

### 4. Implementation Plan

Pseudocode per file - no actual code yet.

```markdown
## Implementation Plan

### File: src/types/User.ts (NEW)
1. Define UserProfile interface from API response
2. Define UserProfileUpdate interface for form
3. Define error types

### File: src/hooks/useUserProfile.ts (NEW)
1. Fetch user profile on mount
2. Handle loading/error states
3. Export data and status

### File: src/components/UserProfile.tsx (NEW)
1. Call useUserProfile hook
2. Show loading skeleton
3. Render form with prefilled data
4. Handle submission
5. Show success/error toast

### File: src/pages/Settings.tsx (MODIFIED)
1. Import UserProfile component
2. Add to page layout
3. Remove old hardcoded user section
```

### 5. Modified Files

```markdown
## Modified Files

- NEW: src/types/User.ts
- NEW: src/hooks/useUserProfile.ts
- NEW: src/components/UserProfile.tsx
- MODIFIED: src/pages/Settings.tsx
- MODIFIED: src/services/apiClient.ts
- DELETE: src/components/OldUserProfile.js
```

### 6. Blockers/Assumptions

```markdown
## Blockers/Assumptions

- Assuming Bearer token is already configured
- Assuming Redux is available in project
- Need clarification: Should avatar upload be included?
```

---

## Full Example

```markdown
# API Integration Plan: User Profile Management

## Overview
- APIs: GET /users/:id, PUT /users/:id
- Files: 3 new, 2 modified, 1 deleted
- Out of scope: Avatar upload, user deletion (separate tickets)

## API Validation Report

✓ GET /users/:id works, returns user object
✓ PUT /users/:id works for updates
✓ Response schema matches OpenAPI spec
⚠ Avatar field sometimes null (confirmed: expected behavior)
⚠ Initial load ~2-3 seconds
✓ Auth: Uses existing Bearer token

## Design Decisions

[DECISION 1] Component location?
  Option A: src/modules/users/UserProfile.tsx
  Option B: src/components/User/Profile.tsx
  → Question: Which matches your architecture?

[DECISION 2] Data fetching?
  Codebase uses Redux
  → Question: Redux or React Query here?

## Implementation Plan

### src/types/User.ts (NEW)
1. Define UserProfile interface
2. Define error types

### src/hooks/useUserProfile.ts (NEW)
1. Fetch profile on mount
2. Handle loading/error
3. Return data + status

### src/components/UserProfile.tsx (NEW)
1. Use hook, show skeleton while loading
2. Render form, handle submit
3. Show toast on success/error

### src/pages/Settings.tsx (MODIFIED)
1. Import and add UserProfile component

## Modified Files

- NEW: src/types/User.ts
- NEW: src/hooks/useUserProfile.ts
- NEW: src/components/UserProfile.tsx
- MODIFIED: src/pages/Settings.tsx
- DELETE: src/components/OldUserInfo.js

## Blockers/Assumptions

- Bearer token configured
- Redux available
- Question: Include avatar upload or separate?
```
