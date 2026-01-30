# Data Safety Rules

**CRITICAL: Protect production/user data at all costs.**

When validating APIs, you will call endpoints with test data. These rules prevent disasters.

---

## The Golden Rule

🔴 **NEVER modify or delete data without `[AGENT-TEST]` or `agent-test-` markers.**

---

## Test Data Naming Convention

All test data created by the agent MUST be clearly identifiable so it can be safely deleted later.

| Field Type | Naming Convention | Example |
|------------|-------------------|---------|
| Title/Name | Prefix with `[AGENT-TEST]` | `[AGENT-TEST] Discount Code` |
| Description | Include marker | `Agent testing - safe to delete` |
| Code/Slug | Prefix with `agent-test-` | `agent-test-promo-50` |
| Email | Use test domain | `agent-test@example.com` |
| Any other field | Use marker if possible | `[AGENT-TEST] Test Value` |

---

## POST (Create) Rules

When creating test data:

1. **Always use naming convention above**
2. **Set inactive flags** - If `isActive`, `status`, `enabled` fields exist, set to `false` to avoid affecting live systems
3. **Note the created ID** - You'll need it for cleanup

**Example:**
```json
{
  "discountName": "[AGENT-TEST] CLI Demo Discount",
  "description": "Agent testing - safe to delete",
  "couponCode": "AGENT-TEST-DEMO50",
  "isActive": false,
  "status": "draft"
}
```

---

## PUT/PATCH (Update) Rules

**CRITICAL RESTRICTION:**

⛔ **ONLY update data that the agent itself created**

Before updating ANY record:

1. Call GET to retrieve the record
2. Check response for agent markers: `[AGENT-TEST]` or `agent-test-`
3. **Only proceed if markers are present**
4. **If markers NOT present, DO NOT UPDATE. Ask user first.**

**Example Safe Update:**
```bash
# First, GET the record
.agent/api.sh GET /endpoint/abc123

# Check response:
# ✓ SAFE if it contains: "[AGENT-TEST]" or "agent-test-"
# ✗ UNSAFE if markers NOT present

# Only if markers exist, proceed with update:
.agent/api.sh PUT /endpoint/abc123 -j '{"status": "active"}'
```

---

## DELETE Rules

**CRITICAL RESTRICTION:**

⛔ **ONLY delete data that the agent itself created**

Before deleting ANY record:

1. Call GET to retrieve the record
2. Check response has agent-test markers
3. **Only delete if markers are present**
4. **If markers NOT present, DO NOT DELETE. Ask user first.**

**Example Safe Delete:**
```bash
# Verify before delete
.agent/api.sh GET /endpoint/abc123

# Check for markers in response
# Response should contain "[AGENT-TEST]" or "agent-test-"

# Only then:
.agent/api.sh DELETE /endpoint/abc123

# Verify deletion
.agent/api.sh GET /endpoint/abc123  # Should return 404
```

---

## What to NEVER Do

❌ Delete or modify records without agent-test markers
❌ Bulk delete operations (e.g., `DELETE /all`)
❌ Update critical fields on non-test records
❌ Create test data without proper markers
❌ Leave `isActive: true` or `status: active` on test records
❌ Assume test data from previous runs still exists (always verify)
❌ Test on production data

---

## Cleanup After Testing

After successful API validation:

1. **List all agent-created test data** - Grep responses for `[AGENT-TEST]` or `agent-test-` markers
2. **Offer to clean up** - Ask user if they want you to delete test entries
3. **Only delete entries with markers** - Never delete anything else
4. **Verify deletion** - Confirm records are gone

**Example cleanup:**
```bash
# List test records created
.agent/api.sh GET /endpoint -q tag=agent-test
# Response shows: [AGENT-TEST] Test1, agent-test-code-2, etc.

# Ask user: "Should I delete these 3 test records?"

# If yes, delete each one:
.agent/api.sh DELETE /endpoint/id1
.agent/api.sh DELETE /endpoint/id2
.agent/api.sh DELETE /endpoint/id3

# Verify:
.agent/api.sh GET /endpoint -q tag=agent-test
# Response should be empty
```

---

## When to Ask User First

🟡 **Ask before proceeding if:**

- You need to test PUT/PATCH on existing (non-test) data
- You're unsure whether a record is test data or real data
- You need to test DELETE on anything without markers
- You found data that might be production data
- You're testing on staging/production environments (vs. dev)

**Always err on the side of caution. Ask if you're not 100% sure.**

---

## Security Levels in api.sh

The `.agent/api.sh` script has security levels that prevent dangerous operations:

- `read-only` - GET only (safe)
- `safe-updates` - GET, POST, PUT, PATCH (risky if you target wrong data)
- `full-access` - All methods including DELETE (dangerous)

Check `.agent/api.sh` for current security level before testing.

---

## Summary

✓ Always use `[AGENT-TEST]` markers
✓ Always verify before update/delete
✓ Always ask if unsure
✓ Always clean up after validation

❌ Never modify production data
❌ Never delete without markers
❌ Never assume previous test data still exists

**When in doubt: DO NOT DELETE. Ask the user.**
