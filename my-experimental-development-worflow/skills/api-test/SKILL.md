---
name: api-test
description: Validates API integration test cases using headless browser automation. Use after implementing an API integration to verify it works correctly in the UI. Runs through test cases from the integration plan.
allowed-tools: Bash(agent-browser:*), Read
argument-hint: [test-plan-or-url]
---

# API Integration Testing

Validates implemented API integrations by running test cases in a headless browser using the `agent-browser` tool.

## Prerequisites

1. API integration has been implemented
2. Local dev server is running
3. Test cases are defined (from `/api-plan` or user-provided)
4. User has explicitly requested testing

## Workflow

### Step 1: Confirm Test Environment

Ask user to confirm:
- Local dev server URL (e.g., `http://localhost:3000`)
- Any authentication/login requirements
- Which test cases to run

### Step 2: Initialize Browser

```bash
# Open the application
agent-browser open http://localhost:[PORT]

# Take initial snapshot to understand the page
agent-browser snapshot -i
```

### Step 3: Handle Authentication (if needed)

If the app requires login:

```bash
# Navigate to login page
agent-browser open http://localhost:[PORT]/login

# Get interactive elements
agent-browser snapshot -i

# Fill login form (refs from snapshot)
agent-browser fill @e1 "test-user@example.com"
agent-browser fill @e2 "password"
agent-browser click @e3

# Wait for redirect
agent-browser wait --url "**/dashboard"
# Or wait for specific element
agent-browser wait --text "Welcome"

# Optionally save auth state for reuse
agent-browser state save auth.json
```

### Step 4: Execute Test Cases

For each test case from the plan:

**Test Case Template:**
```bash
# 1. Navigate to feature
agent-browser open http://localhost:[PORT]/feature-path
agent-browser wait --load networkidle

# 2. Snapshot the page
agent-browser snapshot -i

# 3. Perform action (based on test case)
agent-browser click @eN          # Click button
agent-browser fill @eN "value"   # Fill input
agent-browser select @eN "opt"   # Select dropdown

# 4. Wait for response
agent-browser wait --load networkidle
# Or wait for specific indicator
agent-browser wait --text "Success"

# 5. Verify result
agent-browser snapshot -i
agent-browser get text @eN       # Get result text
agent-browser screenshot         # Capture for evidence

# 6. Check for errors
agent-browser console            # Check console for errors
agent-browser errors             # Check page errors
```

### Step 5: Test Case Categories

**Happy Path Tests:**
- Complete the primary user flow
- Verify data appears correctly
- Check success messages/toasts

**Error Handling Tests:**
```bash
# Test validation errors
agent-browser fill @input ""     # Empty required field
agent-browser click @submit
agent-browser wait --text "required"  # Wait for error message

# Test network errors (if possible)
agent-browser set offline on
agent-browser click @submit
agent-browser wait --text "error"
agent-browser set offline off
```

**Loading State Tests:**
```bash
# Check loading indicators appear
agent-browser click @submit
# Quickly snapshot to catch loading state
agent-browser snapshot -i
# Then wait for completion
agent-browser wait --load networkidle
```

**Edge Case Tests:**
```bash
# Empty state
agent-browser open http://localhost:[PORT]/feature?empty=true
agent-browser snapshot -i
agent-browser get text @emptyMessage

# Large data
agent-browser open http://localhost:[PORT]/feature?limit=100
agent-browser wait --load networkidle
agent-browser get count ".list-item"
```

### Step 6: Record Evidence

For important tests or failures:

```bash
# Screenshot specific state
agent-browser screenshot ./test-evidence/test-name.png

# Full page screenshot
agent-browser screenshot ./test-evidence/full-page.png --full

# Record video of flow (optional)
agent-browser record start ./test-evidence/flow.webm
# ... perform actions ...
agent-browser record stop
```

### Step 7: Report Results

After running all tests, compile a report:

```markdown
# Test Results: [Feature Name]

## Environment
- URL: http://localhost:[PORT]
- Date: [timestamp]
- Browser: Chromium (headless)

## Test Summary
| Test Case | Status | Notes |
|-----------|--------|-------|
| Happy path - Create | PASS | |
| Happy path - Edit | PASS | |
| Error - Validation | PASS | Shows inline error |
| Error - Network | FAIL | No error message shown |

## Passed Tests (X/Y)

### [Test Name]
- Steps completed successfully
- Expected result: [what should happen]
- Actual result: [what happened]

## Failed Tests

### [Test Name]
- Step failed at: [which step]
- Expected: [expected behavior]
- Actual: [actual behavior]
- Screenshot: [path if captured]
- Console errors: [any errors]

## Recommendations
- [Fix needed for failed tests]
- [Improvements suggested]
```

### Step 8: Cleanup

```bash
# Close browser when done
agent-browser close
```

## Common Patterns

### Form Submission Flow
```bash
agent-browser open http://localhost:3000/form
agent-browser snapshot -i
agent-browser fill @name "Test Name"
agent-browser fill @email "test@example.com"
agent-browser select @category "Option 1"
agent-browser check @terms
agent-browser click @submit
agent-browser wait --text "Success"
agent-browser snapshot -i
```

### CRUD Operations
```bash
# Create
agent-browser click @addButton
agent-browser fill @field "New Item"
agent-browser click @save
agent-browser wait --text "Created"

# Read (verify in list)
agent-browser snapshot -i
agent-browser get text @listItem

# Update
agent-browser click @editButton
agent-browser fill @field "Updated Item"
agent-browser click @save
agent-browser wait --text "Updated"

# Delete
agent-browser click @deleteButton
agent-browser click @confirmDelete
agent-browser wait --text "Deleted"
```

### Pagination
```bash
agent-browser get count ".item"        # Count current items
agent-browser click @nextPage
agent-browser wait --load networkidle
agent-browser get count ".item"        # Verify new items loaded
```

## Important Notes

- **Always wait** for network/DOM changes before asserting
- **Re-snapshot** after navigation or significant DOM changes
- **Check console** for JavaScript errors after each major action
- **Use refs** from the most recent snapshot
- **Report failures immediately** - don't continue if critical flow breaks
- **Screenshots are valuable** - capture state at failure points
