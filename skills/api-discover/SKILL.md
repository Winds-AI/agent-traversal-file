---
name: api-discover
description: Discovers and validates API endpoints for integration tasks. Use when user mentions "API integration", "new API", "API changes", "check API", or needs to understand backend endpoint structure before coding. Searches OpenAPI spec and tests endpoints live.
allowed-tools: Bash(api.sh:*), Read, Grep, Glob
argument-hint: [api-path-or-keyword]
---

# API Discovery & Validation

Discover API structure using MCP's `openapi_searchEndpoints` tool and validate endpoints with live calls using the project's `.agent/api.sh` script.

## Workflow

### Step 1: Discover API Structure

Use the `openapi_searchEndpoints` MCP tool to search the backend's OpenAPI/Swagger spec:

```
Call MCP tool: openapi_searchEndpoints
Input: { "path": "$ARGUMENTS" }
```

This returns:
- Endpoint path, method, operationId
- Parameters (query, path, body)
- Request body schema with field types and validation
- Response schemas (success and error)
- Integration hints

### Step 2: Validate APIs with Live Calls

After discovering endpoints, test them using the project's API script.

**Script location:** Look for `.agent/api.sh` in the project root.

**Security levels** (configured in api.sh):
- `read-only`: GET only
- `safe-updates`: GET, POST, PUT, PATCH
- `full-access`: All methods including DELETE

**Basic usage:**
```bash
# GET request with query params
.agent/api.sh GET /endpoint-path -q page=1 -q limit=10

# POST with JSON body
.agent/api.sh POST /endpoint-path -j '{"field": "value"}'

# PUT update
.agent/api.sh PUT /endpoint-path/id -j '{"field": "updated"}'

# PATCH partial update
.agent/api.sh PATCH /endpoint-path/id -j '{"status": "active"}'

# DELETE (requires full-access security level)
.agent/api.sh DELETE /endpoint-path/id
```

**Advanced options:**
- `-q key=value` - Add query parameter (repeatable)
- `-j '{"json": "body"}'` - JSON request body
- `-j @file.json` - JSON body from file
- `-F key=value` - Multipart form field
- `-F file=@/path/to/file` - File upload
- `-H 'Header: Value'` - Extra header
- `--no-pretty` - Disable JSON formatting

### Step 3: Analyze Results

For each endpoint tested:

1. **Check response status** - 2xx means success
2. **Verify response schema** matches OpenAPI spec
3. **Note any discrepancies** between spec and actual response
4. **Document required fields** and their types
5. **Identify pagination patterns** (page/limit, cursor, offset)
6. **Note authentication requirements**

### Step 4: Report Findings

Provide a summary:

```
## API Discovery Report: [endpoint-path]

### Endpoints Found
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET    | /... | Working | Returns paginated list |
| POST   | /... | Working | Creates new resource |

### Request Schema
- field1: string (required)
- field2: number (optional, default: 0)
- ...

### Response Schema
- data: array of objects
  - id: string
  - ...

### Issues/Warnings
- [Any discrepancies or issues found]

### Ready for Integration
[Yes/No - with explanation]
```

## Data Safety Rules

**CRITICAL: Protect production/user data at all costs.**

### Agent-Created Test Data Convention

All test data created by the agent MUST be clearly identifiable:

| Field Type | Naming Convention | Example |
|------------|-------------------|---------|
| Title/Name | Prefix with `[AGENT-TEST]` | `[AGENT-TEST] Discount Code` |
| Description | Include marker | `Agent testing - safe to delete` |
| Code/Slug | Prefix with `agent-test-` | `agent-test-promo-50` |
| Email | Use test domain | `agent-test@example.com` |

**Example test payload:**
```json
{
  "discountName": "[AGENT-TEST] 50% Off Promo",
  "description": "Agent testing - safe to delete",
  "couponCode": "AGENT-TEST-50OFF",
  "isActive": false
}
```

### POST (Create) Rules
- Always use the naming convention above
- Set `isActive: false` when possible to avoid affecting live systems
- Note the created resource ID for cleanup

### PUT/PATCH (Update) Rules
- **ONLY update data that the agent itself created**
- Before updating, verify the record has agent-test markers
- NEVER update records without `[AGENT-TEST]` or `agent-test-` markers
- If you need to test update on existing data, ASK USER FIRST

```bash
# First, GET the record and check if it's agent-created
.agent/api.sh GET /endpoint/ID

# Only proceed if response contains agent markers
# e.g., name contains "[AGENT-TEST]" or code starts with "agent-test-"
```

### DELETE Rules
- **ONLY delete data that the agent itself created**
- Before deleting, GET the record and verify it has agent-test markers
- NEVER delete records without `[AGENT-TEST]` or `agent-test-` markers
- When in doubt, DO NOT DELETE - ask the user

```bash
# Verify before delete
.agent/api.sh GET /endpoint/ID
# Check response for "[AGENT-TEST]" or "agent-test-" markers
# Only then:
.agent/api.sh DELETE /endpoint/ID
```

### Cleanup After Testing
After successful API validation:
1. List all agent-created test data
2. Offer to clean up (delete) test entries
3. Only delete entries with agent markers

### What to NEVER Do
- Delete or modify records without agent-test markers
- Bulk delete operations (`DELETE /all`, etc.)
- Update critical fields on non-test records
- Create test data without proper markers
- Leave `isActive: true` on test records if avoidable

## Important Notes

- Always test APIs BEFORE proceeding with integration
- If any API returns error status, STOP and inform the user
- If API response differs from spec, document the actual response
- Check security level in api.sh if methods are blocked
- For authenticated endpoints, ensure token is configured in api.sh
- **Always use agent-test markers for any data you create**
- **Never modify or delete data without agent-test markers**

## Example

User: "integrate the discounts API"

1. **Discover:** `openapi_searchEndpoints({ path: "discounts" })`

2. **Test GET (safe, read-only):**
   ```bash
   .agent/api.sh GET /bandar-admin/discounts -q page=1 -q limit=3
   ```

3. **Test POST (create with agent markers):**
   ```bash
   .agent/api.sh POST /bandar-admin/discounts -j '{
     "discountName": "[AGENT-TEST] CLI Demo Discount",
     "description": "Agent testing - safe to delete",
     "discountType": "fixed",
     "discountValue": 50,
     "couponCode": "AGENT-TEST-DEMO50",
     "isActive": false,
     "promoAppliedOn": "service_charge",
     "validFrom": "2025-01-01T00:00:00.000Z",
     "validTo": "2025-12-31T23:59:59.999Z"
   }'
   ```
   Note the created ID from response (e.g., `"id": "abc123"`)

4. **Test PUT (only on agent-created record):**
   ```bash
   # First verify it's our test record
   .agent/api.sh GET /bandar-admin/discounts/abc123
   # Confirm response contains "[AGENT-TEST]" marker, then:
   .agent/api.sh PUT /bandar-admin/discounts/abc123 -j '{
     "discountName": "[AGENT-TEST] Updated Demo Discount",
     "discountValue": 75
   }'
   ```

5. **Test DELETE (only agent-created record):**
   ```bash
   # Verify marker exists before delete
   .agent/api.sh GET /bandar-admin/discounts/abc123
   # Confirm "[AGENT-TEST]" in response, then:
   .agent/api.sh DELETE /bandar-admin/discounts/abc123
   ```

6. **Report findings** with schema details

7. **Cleanup:** Ensure all `[AGENT-TEST]` records are deleted or offer to clean up
