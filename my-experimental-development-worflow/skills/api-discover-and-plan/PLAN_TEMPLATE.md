# Plan Template for API Integration

Your plans must follow this structure. This allows developers to scan and approve in 5-10 minutes.

---

## 1. Overview

**What:** List the API(s) being integrated or updated
**Scope:** How many new/modified/deleted files?
**Boundaries:** What's explicitly NOT included (out of scope)

**Example:**
```
## Overview
- APIs being integrated: GET /users/:id, PUT /users/:id
- Files: 3 new, 2 modified, 1 deleted
- Out of scope: User deletion, role-based access control (separate ticket)
```

---

## 2. API Validation Report

**Your validation findings.** Developer needs to know the API works and matches the spec.

**Structure:**
- Endpoint works as spec says? ✓/✗
- Response format matches spec? ✓/✗
- Any anomalies or surprises?
- Authentication requirements?
- Latency/performance notes?

**Example:**
```
## API Validation Report

✓ GET /users/:id works, returns user object as spec says
✓ Response includes: id, name, email, phone, avatar
⚠ API takes 2-3 seconds on first call (includes avatar processing)
⚠ Avatar field sometimes null even when user has avatar set
? Question: Is the null avatar a backend bug or expected?
```

---

## 3. Design Decisions (with questions)

**Explicit choices.** Format each decision clearly so developer can approve or redirect.

**Structure:**
```
[DECISION N] [Question being answered?]
  Option A: [Description of approach]
  Option B: [Alternative approach]
  → Question for developer: [What should I do?]
```

**Example:**
```
[DECISION 1] Where to put the new UserProfile component?
  Option A: New module at src/modules/users/components/UserProfile.tsx
  Option B: Add to existing src/components/User/Profile.tsx
  → Question: Where fits your modular architecture?

[DECISION 2] State management for user profile data?
  Codebase uses: Redux for global state
  → Question: Should I use Redux or React Query for this feature?

[DECISION 3] Error handling approach?
  Current app shows API errors as: Toast notifications
  → Question: Consistent toast approach or different for this feature?

[DECISION 4] Should cleanup of old UserProfile.js happen?
  → Question: Is removing legacy code in scope or separate?
```

**Note:** Only ask when genuinely ambiguous. Don't ask "should I write clean code?" - of course you should.

---

## 4. Implementation Plan

**Pseudocode/flow** of what will be built, file by file. No actual code yet, just the structure.

**Example:**
```
## Implementation Plan

### File: src/types/User.ts (NEW)
1. Define UserProfile interface from API response
2. Define UserProfileUpdate interface for form submission
3. Define error types (401, 404, etc.)

### File: src/services/userService.ts (NEW)
1. getUserProfile(userId) - calls GET /users/:id
2. updateUserProfile(userId, data) - calls PUT /users/:id
3. Error handling wrapper

### File: src/hooks/useUserProfile.ts (NEW)
1. Fetch user profile on mount
2. Handle loading state
3. Handle error state
4. Export data and loading status

### File: src/components/UserProfile.tsx (NEW)
1. Create component structure
2. Call useUserProfile hook
3. Show loading skeleton while fetching
4. Show error toast if API fails
5. Render form with prefilled data
6. Handle form submission (call updateUserProfile)
7. Show success toast after update

### File: src/pages/UserSettings.tsx (MODIFIED)
1. Import new UserProfile component
2. Add UserProfile to layout
3. Remove old hardcoded user info
```

---

## 5. Modified Files

**What's changing.** Clear list so developer knows scope.

**Format:**
```
- NEW: src/types/User.ts
- NEW: src/hooks/useUserProfile.ts
- NEW: src/components/UserProfile.tsx
- MODIFIED: src/pages/UserSettings.tsx (added UserProfile component)
- MODIFIED: src/services/apiClient.ts (added user endpoints)
- DELETE: src/components/OldUserProfile.js (replaced by new UserProfile.tsx)
```

---

## 6. Blockers or Assumptions

**Anything that needs clarification before you start coding.**

**Examples:**
```
## Blockers/Assumptions
- Assuming API token is already configured in api.sh
- Assuming Redux is available (already imported in your setup)
- Need clarification: Should avatar upload be included? (not in spec)
- Need decision: Max retries on network failure?
```

---

## Full Example Plan

```markdown
# API Integration Plan: User Profile Management

## Overview
- APIs being integrated: GET /users/:id, PUT /users/:id
- Files: 3 new, 2 modified, 1 deleted
- Out of scope: Avatar upload, user deletion, role permissions (separate tickets)

## API Validation Report

✓ GET /users/:id endpoint works, returns user object
✓ Response schema matches OpenAPI spec exactly
✓ PUT /users/:id endpoint works for updates
⚠ Avatar field sometimes null (verified behavior, not a bug)
⚠ API takes ~2-3 seconds on initial calls
✓ Authentication: Uses existing Bearer token config

## Design Decisions

[DECISION 1] Component location?
  Option A: New module at src/modules/users/UserProfile.tsx
  Option B: Add to existing src/components/User/Profile.tsx
  → Question: Where should this live based on your architecture?

[DECISION 2] Data fetching approach?
  Codebase uses: Redux for global state
  Option: Use React Query for component-level data (different from Redux)
  → Question: Should I follow Redux pattern or use React Query here?

[DECISION 3] Error handling?
  Current app: Shows errors via toast notifications
  → Question: Consistent toast or different approach?

## Implementation Plan

### File: src/types/User.ts (NEW)
1. Define UserProfile interface from API
2. Define error response types
3. Export for use in hooks/components

### File: src/hooks/useUserProfile.ts (NEW)
1. Fetch user profile on mount
2. Return: user data, loading state, error state
3. Handle API failures gracefully

### File: src/components/UserProfile.tsx (NEW)
1. Create form component
2. Use useUserProfile hook
3. Show loading skeleton
4. Show error toast if API fails
5. Render form with prefilled data
6. Handle save button (call API)
7. Show success toast

### File: src/pages/Settings.tsx (MODIFIED)
1. Import UserProfile component
2. Add to page layout
3. Remove old hardcoded user section

### File: src/services/apiClient.ts (MODIFIED)
1. Add GET /users/:id endpoint
2. Add PUT /users/:id endpoint

## Modified Files

- NEW: src/types/User.ts
- NEW: src/hooks/useUserProfile.ts
- NEW: src/components/UserProfile.tsx
- MODIFIED: src/pages/Settings.tsx (added UserProfile component)
- MODIFIED: src/services/apiClient.ts (added endpoints)
- DELETE: src/components/OldUserInfo.js

## Blockers/Assumptions

- Assuming Bearer token is configured
- Assuming Redux is available in project
- Question: Should I handle avatar uploads in this feature or separate?
```

---

## Tips for Good Plans

✓ **Scannable** - Use headers, bullets, examples
✓ **Specific** - Actual file paths, actual questions
✓ **Bounded** - Clear what's in and out of scope
✓ **Humble** - Ask questions instead of assuming
✓ **Testable** - Implementation plan should be verifiable
